from typing import Literal

import numpy as np

from swproj.dsp import target_response_db
from swproj.types import F_MAX, F_MIN, Curve, Extremum, Measurement, TargetEq


def local_extrema(
    c: Curve, kind: Literal["peak", "dip"], top: int = 3
) -> list[Extremum]:
    """
    Return the `top` strongest local peaks or dips.

    A local peak satisfies mag[i-1] < mag[i] > mag[i+1] and is sorted by
    descending magnitude (largest positive first).
    A local dip satisfies mag[i-1] > mag[i] < mag[i+1] and is sorted by
    ascending magnitude (most negative first).
    """
    m = c.mag_db
    if kind == "peak":
        mask = (m[1:-1] > m[:-2]) & (m[1:-1] > m[2:])
        order_key = -m
    else:
        mask = (m[1:-1] < m[:-2]) & (m[1:-1] < m[2:])
        order_key = m
    idx = np.where(mask)[0] + 1
    if idx.size == 0:
        return []
    sorted_idx = idx[np.argsort(order_key[idx])][:top]
    return [
        Extremum(freq_hz=float(c.freq_hz[i]), mag_db=float(m[i])) for i in sorted_idx
    ]


def channel_summary(c: Curve, label: str) -> str:
    """
    Format one channel's dynamic range, top peaks, and top dips as a multi-line string.
    """
    peaks = local_extrema(c, "peak", top=3)
    dips = local_extrema(c, "dip", top=3)
    # mean level above 200 hz, where the room contributes less and the
    # speaker's own response dominates
    above = c.freq_hz >= 200.0
    mean_hf = float(np.mean(c.mag_db[above])) if above.any() else float("nan")
    dyn = float(c.mag_db.max() - c.mag_db.min())
    lines = [
        f"  {label}:",
        f"    dynamic range:        {dyn:5.2f} db",
        f"    min / max:           {c.mag_db.min():+5.2f} / {c.mag_db.max():+5.2f} db",
        f"    mean (>= 200 hz):    {mean_hf:+5.2f} db",
        "    top peaks:           "
        + ", ".join(f"{p.freq_hz:6.1f} hz {p.mag_db:+5.2f} db" for p in peaks),
        "    top dips:            "
        + ", ".join(f"{d.freq_hz:6.1f} hz {d.mag_db:+5.2f} db" for d in dips),
    ]
    return "\n".join(lines)


def print_measurement_summary(meas: Measurement) -> None:
    """
    Print a stereo room measurement summary to stdout.
    """
    print(f"measurement: {meas.source.name}")
    print(f"  points:                {meas.left.freq_hz.size}")
    print(
        f"  span:                  {meas.left.freq_hz[0]:.1f} hz "
        f".. {meas.left.freq_hz[-1]:.1f} hz (log-spaced)"
    )
    print(channel_summary(meas.left, "left"))
    print(channel_summary(meas.right, "right"))
    # l-r asymmetry over the band where the room dominates
    band = (meas.left.freq_hz >= 30.0) & (meas.left.freq_hz <= 300.0)
    if band.any():
        diff = np.abs(meas.left.mag_db[band] - meas.right.mag_db[band])
        print(
            f"  L-R asymmetry (30-300 hz):  max {float(diff.max()):.2f} db, "
            f"rms {float(np.sqrt(np.mean(diff**2))):.2f} db"
        )


def print_target_summary(target: TargetEq, fs: float) -> None:
    """
    Print a target EQ filter list and realised composite range to stdout.
    """
    print(f"target eq: {target.source.name}  (name: {target.name!r})")
    if not target.filters:
        print("  no filters")
        return
    for i, f in enumerate(target.filters):
        flag = "" if f.enabled else "  [disabled]"
        print(
            f"  [{i}] {f.type:>10}  f={f.freq_hz:7.1f} hz  "
            f"gain={f.gain_db:+5.2f} db  Q={f.q:.2f}{flag}"
        )
    grid = np.logspace(np.log10(F_MIN), np.log10(F_MAX), 4096)
    h = target_response_db(target, fs, grid)
    print(
        f"  realised over 20-22k hz:  "
        f"max {h.max():+.2f} db at {grid[h.argmax()]:.1f} hz, "
        f"min {h.min():+.2f} db at {grid[h.argmin()]:.1f} hz"
    )
