from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

import numpy as np
from numpy.typing import NDArray

type FloatArr = NDArray[np.float64]


# SoundID measurement grid from sweeps is 355 log spaced points from 20 hz to 22000 hz
N_POINTS: Final[int] = 355
F_MIN: Final[float] = 20.0
F_MAX: Final[float] = 22000.0


# Biquad filter types match the target EQ json format, string values must be kebab case
class BiquadType(StrEnum):
    BELL = "bell"
    LOW_SHELF = "low-shelf"
    HIGH_SHELF = "high-shelf"


@dataclass(frozen=True)
class BiquadSpec:
    type: BiquadType
    freq_hz: float
    gain_db: float
    q: float
    enabled: bool = True


@dataclass(frozen=True)
class TargetEq:
    name: str
    filters: tuple[BiquadSpec, ...]
    source: Path


@dataclass(frozen=True)
class Extremum:
    freq_hz: float
    mag_db: float


@dataclass(frozen=True)
class Curve:
    """
    Log spaced frequency response, magnitude in db.
    """

    freq_hz: FloatArr
    mag_db: FloatArr


@dataclass(frozen=True)
class Measurement:
    """
    Stereo room measurement extracted from a .swproj file.
    """

    left: Curve
    right: Curve
    source: Path
