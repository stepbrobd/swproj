from typing import Literal

import numpy as np

from swproj.types import Curve, Extremum


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
