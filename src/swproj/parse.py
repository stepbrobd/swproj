import json
from pathlib import Path
from typing import NotRequired, TypedDict

from swproj.types import (
    BiquadSpec,
    BiquadType,
    TargetEq,
)


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
