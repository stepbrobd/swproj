import json
import struct
from pathlib import Path
from typing import NotRequired, TypedDict

import numpy as np

from swproj.types import (
    F_MAX,
    F_MIN,
    N_POINTS,
    BiquadSpec,
    BiquadType,
    Curve,
    FloatArr,
    Measurement,
    TargetEq,
)


def log_freq_grid(
    n: int = N_POINTS, fmin: float = F_MIN, fmax: float = F_MAX
) -> FloatArr:
    """
    SoundID uses log-spaced points: f[i] = fmin * (fmax/fmin)^(i/(n-1)).
    """
    i = np.arange(n, dtype=np.float64)
    return fmin * (fmax / fmin) ** (i / (n - 1))


def _candidate_offsets(data: bytes, start: int) -> list[int]:
    """
    Positions of float32 20.0 in `data` at or after `start`.
    """
    needle = struct.pack("<f", F_MIN)
    out: list[int] = []
    p = start
    while True:
        p = data.find(needle, p + 1)
        if p < 0:
            break
        out.append(p)
    return out


def _try_read_curve(data: bytes, off: int, stride: int, grid: FloatArr) -> Curve | None:
    """
    Try to read 355 floats at offset `off` with given stride.

    Returns a curve if the frequency column matches the expected log grid, o.w. None.
    """
    total = N_POINTS * stride
    need = total * 4
    if off + need > len(data):
        return None
    vals = np.frombuffer(data[off : off + need], dtype="<f4").astype(np.float64)
    freqs = vals[0::stride]
    # tight tolerance because the grid is deterministic
    if not np.allclose(freqs, grid, rtol=1e-4, atol=1e-2):
        return None
    mags = vals[1::stride]
    return Curve(freq_hz=freqs.copy(), mag_db=mags.copy())


def parse_swproj(path: Path) -> Measurement:
    """
    Parse SoundID .swproj file and return the measurement.
    Corrections are not returned as they are exactly the negation of measurement with phase zero.

    File format:
        bytes 0..xml_end:    project header xml
        bytes ..peqb:        small padding then b'PEQb' magic
        bytes peqb..:        repeated sections, each is 355 little-endian
                             float32 values interleaved as (freq, mag) for
                             measurement sections or (freq, gain, phase) for
                             "correction" sections
    """
    data = path.read_bytes()
    xml_end = data.find(b"</ProjectHeader>")
    if xml_end < 0:
        raise ValueError(f"{path}: missing <ProjectHeader>, not a swproj file")
    peqb = data.find(b"PEQb", xml_end)
    if peqb < 0:
        raise ValueError(f"{path}: missing PEQb block")

    grid = log_freq_grid()
    measurements: list[Curve] = []
    seen: set[int] = set()

    # scan all float32 20.0 occurrences after the peqb header
    # each marks the start of a curve
    for off in _candidate_offsets(data, peqb):
        if off in seen:
            continue
        curve = _try_read_curve(data, off, stride=2, grid=grid)
        if curve is None:
            continue
        # reject if values look like freq (huge) or phases (tiny constant zero)
        if np.max(np.abs(curve.mag_db)) > 60.0:
            continue
        if np.all(np.abs(curve.mag_db) < 1e-9):
            continue
        measurements.append(curve)
        seen.add(off)

    if len(measurements) < 2:
        raise ValueError(
            f"{path}: expected at least 2 measurement curves (L, R), "
            f"found {len(measurements)}"
        )

    # the file layout writes left first, then the left correction
    #                   then right,      then right correction
    # the first two valid curves are the left and right measurements
    return Measurement(left=measurements[0], right=measurements[1], source=path)


class _RawFilter(TypedDict):
    type: str
    frequency: float
    gain: float
    q: float
    enabled: NotRequired[bool]


def _parse_biquad(d: _RawFilter) -> BiquadSpec:
    try:
        t = BiquadType(d["type"])
    except ValueError as e:
        raise ValueError(f"Unsupported filter type: {d['type']!r}") from e
    return BiquadSpec(
        type=t,
        freq_hz=float(d["frequency"]),
        gain_db=float(d["gain"]),
        q=float(d["q"]),
        enabled=d.get("enabled", True),
    )


def parse_target_json(path: Path) -> TargetEq:
    """Parse a target EQ export.

    Schema:
        {
            "name": str,
            "filterGroups": [ { "filters": [ {type, frequency, gain, q, enabled}, ... ] } ]
        }
    """
    raw = json.loads(path.read_text())
    name = str(raw.get("name", path.stem))
    groups = raw.get("filterGroups", [])
    if not groups:
        raise ValueError(f"{path}: no filterGroups in target json")
    filters_raw: list[_RawFilter] = []
    for g in groups:
        filters_raw.extend(g.get("filters", []))
    filters = tuple(_parse_biquad(f) for f in filters_raw)
    return TargetEq(name=name, filters=filters, source=path)
