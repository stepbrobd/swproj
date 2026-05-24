from typing import assert_never

import numpy as np
import yaml

from swproj.types import (
    F_MAX,
    F_MIN,
    BiquadSpec,
    BiquadType,
    ComplexArr,
    Curve,
    FilterPhase,
    FloatArr,
    Measurement,
    TargetEq,
)


class _FlowList(list[object]):
    pass


class _CompactDumper(yaml.SafeDumper):
    pass


def _represent_flow_list(dumper: yaml.SafeDumper, data: _FlowList) -> yaml.SequenceNode:
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


def _represent_float(dumper: yaml.SafeDumper, value: float) -> yaml.ScalarNode:
    text = f"{value:.7g}"
    if "." not in text and "e" not in text:
        text += ".0"
    return dumper.represent_scalar("tag:yaml.org,2002:float", text)


_CompactDumper.add_representer(_FlowList, _represent_flow_list)
_CompactDumper.add_representer(float, _represent_float)


def _quantize_fir(h: FloatArr) -> FloatArr:
    """
    Snap each coefficient to the nearest float32, then widen back to float64.
    ~7 sigfigs is below audibility for a RC FIR.
    """
    return h.astype(np.float32).astype(np.float64)


def _min_phase_spectrum(mag_lin: FloatArr) -> ComplexArr:
    """
    Complex rfft-layout spectrum with minimum-phase characteristic from a
    positive-frequency magnitude. Real-cepstrum fold method (Oppenheim &
    Schafer 13.5).
    """
    n_half = mag_lin.size
    n = 2 * (n_half - 1)
    log_mag = np.log(np.maximum(mag_lin, 1e-12))
    full = np.concatenate([log_mag, log_mag[-2:0:-1]])
    cepstrum: FloatArr = np.fft.ifft(full).real
    fold = np.zeros_like(cepstrum)
    fold[0] = cepstrum[0]
    fold[n // 2] = cepstrum[n // 2]
    fold[1 : n // 2] = 2.0 * cepstrum[1 : n // 2]
    spectrum: ComplexArr = np.exp(np.fft.fft(fold))
    return spectrum[:n_half]


def _causal_taper(n: int) -> FloatArr:
    w = np.ones(n, dtype=np.float64)
    half = np.hanning(n)[n // 2 :]
    w[n // 2 :] = half
    return w


def correction_fir(
    curve: Curve,
    rate: int,
    taps: int,
    max_boost_db: float,
    phase: FilterPhase,
) -> FloatArr:
    n_half = taps // 2 + 1
    corr_db = np.minimum(-curve.mag_db, max_boost_db)

    f_lin = np.linspace(0.0, rate / 2.0, n_half)
    log_f_lin = np.log(np.maximum(f_lin, 1e-6))
    log_f_curve = np.log(curve.freq_hz)

    in_band = (f_lin >= F_MIN) & (f_lin <= F_MAX)
    corr_lin_db = np.zeros(n_half, dtype=np.float64)
    corr_lin_db[in_band] = np.interp(log_f_lin[in_band], log_f_curve, corr_db)
    mag_lin = 10.0 ** (corr_lin_db / 20.0)

    match phase:
        case FilterPhase.LINEAR:
            h = np.fft.irfft(mag_lin.astype(np.complex128), n=taps)
            h = np.fft.fftshift(h) * np.hanning(taps)
        case FilterPhase.MINIMUM:
            spectrum = _min_phase_spectrum(mag_lin)
            h = np.fft.irfft(spectrum, n=taps) * _causal_taper(taps)
        case _:
            assert_never(phase)

    return _quantize_fir(h.astype(np.float64))


def _biquad_params(spec: BiquadSpec) -> dict[str, object]:
    match spec.type:
        case BiquadType.BELL:
            kind = "Peaking"
        case BiquadType.LOW_SHELF:
            kind = "Lowshelf"
        case BiquadType.HIGH_SHELF:
            kind = "Highshelf"
        case _:
            assert_never(spec.type)
    return {
        "type": kind,
        "freq": float(spec.freq_hz),
        "gain": float(spec.gain_db),
        "q": float(spec.q),
    }


def _biquad_name(idx: int, spec: BiquadSpec) -> str:
    kind = spec.type.value.replace("-", "_")
    return f"target_{idx:02d}_{kind}_{int(spec.freq_hz)}"


def build_config(
    measurement: Measurement | None,
    target: TargetEq | None,
    rate: int,
    taps: int,
    max_boost_db: float,
    phase: FilterPhase,
) -> dict[str, object]:
    filters: dict[str, object] = {}

    if measurement is not None:
        for name, curve in (
            ("room_left", measurement.left),
            ("room_right", measurement.right),
        ):
            ir = correction_fir(curve, rate, taps, max_boost_db, phase)
            filters[name] = {
                "type": "Conv",
                "parameters": {
                    "type": "Values",
                    "values": _FlowList(float(x) for x in ir),
                },
            }

    target_names: list[str] = []
    if target is not None:
        for i, f in enumerate(target.filters):
            if not f.enabled:
                continue
            name = _biquad_name(i, f)
            target_names.append(name)
            filters[name] = {
                "type": "Biquad",
                "parameters": _biquad_params(f),
            }

    left_chain: list[str] = []
    right_chain: list[str] = []
    if measurement is not None:
        left_chain.append("room_left")
        right_chain.append("room_right")
    left_chain.extend(target_names)
    right_chain.extend(target_names)

    pipeline: list[dict[str, object]] = [
        {"type": "Filter", "channels": _FlowList([0]), "names": _FlowList(left_chain)},
        {"type": "Filter", "channels": _FlowList([1]), "names": _FlowList(right_chain)},
    ]

    return {"filters": filters, "pipeline": pipeline}


def emit_yaml(config: dict[str, object]) -> str:
    return yaml.dump(
        config,
        Dumper=_CompactDumper,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
