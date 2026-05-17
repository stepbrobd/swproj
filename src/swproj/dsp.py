from typing import assert_never

import numpy as np

from swproj.types import BiquadSpec, BiquadType, FloatArr, TargetEq


def biquad_mag_db(spec: BiquadSpec, fs: float, freqs: FloatArr) -> FloatArr:
    """
    Biquad magnitude response in db at `freqs` (hz) for sample rate fs.
    https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html
    https://www.w3.org/TR/audio-eq-cookbook/
    """
    w0 = 2.0 * np.pi * spec.freq_hz / fs
    a = 10.0 ** (spec.gain_db / 40.0)
    alpha = np.sin(w0) / (2.0 * spec.q)
    cw = np.cos(w0)
    sa = np.sqrt(a)

    match spec.type:
        case BiquadType.BELL:
            b0, b1, b2 = 1.0 + alpha * a, -2.0 * cw, 1.0 - alpha * a
            a0, a1, a2 = 1.0 + alpha / a, -2.0 * cw, 1.0 - alpha / a
        case BiquadType.LOW_SHELF:
            b0 = a * ((a + 1.0) - (a - 1.0) * cw + 2.0 * sa * alpha)
            b1 = 2.0 * a * ((a - 1.0) - (a + 1.0) * cw)
            b2 = a * ((a + 1.0) - (a - 1.0) * cw - 2.0 * sa * alpha)
            a0 = (a + 1.0) + (a - 1.0) * cw + 2.0 * sa * alpha
            a1 = -2.0 * ((a - 1.0) + (a + 1.0) * cw)
            a2 = (a + 1.0) + (a - 1.0) * cw - 2.0 * sa * alpha
        case BiquadType.HIGH_SHELF:
            b0 = a * ((a + 1.0) + (a - 1.0) * cw + 2.0 * sa * alpha)
            b1 = -2.0 * a * ((a - 1.0) + (a + 1.0) * cw)
            b2 = a * ((a + 1.0) + (a - 1.0) * cw - 2.0 * sa * alpha)
            a0 = (a + 1.0) - (a - 1.0) * cw + 2.0 * sa * alpha
            a1 = 2.0 * ((a - 1.0) - (a + 1.0) * cw)
            a2 = (a + 1.0) - (a - 1.0) * cw - 2.0 * sa * alpha
        case _:
            assert_never(spec.type)

    w = 2.0 * np.pi * freqs / fs
    ejw = np.exp(-1j * w)
    h = (b0 + b1 * ejw + b2 * ejw**2) / (a0 + a1 * ejw + a2 * ejw**2)
    mag: FloatArr = 20.0 * np.log10(np.abs(h) + 1e-30)
    return mag


def target_response_db(target: TargetEq, fs: float, freqs: FloatArr) -> FloatArr:
    """
    Sum of enabled biquad magnitudes in db.
    """
    out: FloatArr = np.zeros_like(freqs)
    for f in target.filters:
        if not f.enabled:
            continue
        out = out + biquad_mag_db(f, fs, freqs)
    return out
