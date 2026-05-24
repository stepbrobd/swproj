import json
from typing import assert_never

from swproj.camilladsp import correction_fir
from swproj.types import (
    BiquadSpec,
    BiquadType,
    FilterPhase,
    FloatArr,
    Measurement,
    TargetEq,
)


_SINK_NAME = "swproj_corrected"
_MODULE_NAME = "libpipewire-module-filter-chain"


def _bq_label(t: BiquadType) -> str:
    match t:
        case BiquadType.BELL:
            return "bq_peaking"
        case BiquadType.LOW_SHELF:
            return "bq_lowshelf"
        case BiquadType.HIGH_SHELF:
            return "bq_highshelf"
        case _:
            assert_never(t)


def _inline_ir(samples: FloatArr, rate: int) -> str:
    """PipeWire convolver inline IR syntax: '/ir:<rate>,<v1>,<v2>,...'."""
    parts = ",".join(f"{x:.7g}" for x in samples)
    return f"/ir:{rate},{parts}"


def _conv_node(ch: str, samples: FloatArr, rate: int) -> dict[str, object]:
    return {
        "type": "builtin",
        "label": "convolver",
        "name": f"conv_{ch}",
        "config": {"filename": _inline_ir(samples, rate)},
    }


def _bq_node(idx: int, spec: BiquadSpec, ch: str) -> dict[str, object]:
    return {
        "type": "builtin",
        "label": _bq_label(spec.type),
        "name": f"bq{idx:02d}_{ch}",
        "control": {
            "Freq": float(spec.freq_hz),
            "Q": float(spec.q),
            "Gain": float(spec.gain_db),
        },
    }


def _channel_chain(
    ch: str,
    ir: FloatArr | None,
    rate: int,
    biquads: tuple[BiquadSpec, ...],
) -> tuple[str, str, list[dict[str, object]], list[dict[str, object]]]:
    nodes: list[dict[str, object]] = []
    stages: list[str] = []

    if ir is not None:
        node = _conv_node(ch, ir, rate)
        nodes.append(node)
        stages.append(f"conv_{ch}")

    for i, spec in enumerate(biquads):
        if not spec.enabled:
            continue
        nodes.append(_bq_node(i, spec, ch))
        stages.append(f"bq{i:02d}_{ch}")

    if not stages:
        raise ValueError(f"empty filter chain for channel {ch!r}")

    links: list[dict[str, object]] = [
        {"output": f"{a}:Out", "input": f"{b}:In"}
        for a, b in zip(stages, stages[1:])
    ]
    return f"{stages[0]}:In", f"{stages[-1]}:Out", nodes, links


def build_config(
    measurement: Measurement | None,
    target: TargetEq | None,
    rate: int,
    taps: int,
    max_boost_db: float,
    phase: FilterPhase,
) -> dict[str, object]:
    ir_l: FloatArr | None = None
    ir_r: FloatArr | None = None
    if measurement is not None:
        ir_l = correction_fir(measurement.left, rate, taps, max_boost_db, phase)
        ir_r = correction_fir(measurement.right, rate, taps, max_boost_db, phase)

    biquads = target.filters if target is not None else ()
    in_l, out_l, nodes_l, links_l = _channel_chain("l", ir_l, rate, biquads)
    in_r, out_r, nodes_r, links_r = _channel_chain("r", ir_r, rate, biquads)

    args: dict[str, object] = {
        "node.description": "swproj Room Correction",
        "media.name": "swproj Room Correction",
        "filter.graph": {
            "nodes": nodes_l + nodes_r,
            "links": links_l + links_r,
            "inputs": [in_l, in_r],
            "outputs": [out_l, out_r],
        },
        "capture.props": {
            "node.name": _SINK_NAME,
            "media.class": "Audio/Sink",
            "audio.channels": 2,
            "audio.position": ["FL", "FR"],
        },
        "playback.props": {
            "node.name": f"{_SINK_NAME}_out",
            "audio.position": ["FL", "FR"],
            "node.passive": True,
        },
    }

    return {"context.modules": [{"name": _MODULE_NAME, "args": args}]}


def emit_conf(config: dict[str, object]) -> str:
    return json.dumps(config, indent=2) + "\n"
