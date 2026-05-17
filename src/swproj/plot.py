from pathlib import Path
from typing import Final

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from swproj.dsp import biquad_mag_db, target_response_db
from swproj.types import F_MAX, F_MIN, Measurement, TargetEq

matplotlib.use("Agg")


# Nord dark palette
NORD: Final[dict[str, str]] = {
    "bg": "#2e3440",
    "panel": "#3b4252",
    "grid": "#4c566a",
    "fg": "#eceff4",
    "frost": "#88c0d0",
    "frost_deep": "#5e81ac",
    "red": "#bf616a",
    "yellow": "#ebcb8b",
    "green": "#a3be8c",
    "purple": "#b48ead",
    "orange": "#d08770",
}


def _style(ax: Axes, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_facecolor(NORD["panel"])
    ax.set_title(title, color=NORD["fg"])
    ax.set_xlabel(xlabel, color=NORD["fg"])
    ax.set_ylabel(ylabel, color=NORD["fg"])
    ax.grid(True, which="both", color=NORD["grid"], alpha=0.4, linewidth=0.5)
    ax.axhline(0, color=NORD["grid"], linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color(NORD["grid"])
    ax.tick_params(colors=NORD["fg"], which="both")


def plot_measurement(meas: Measurement, out: Path) -> None:
    """
    Render a stereo room measurement as a left/right semilog plot.
    """
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.semilogx(
        meas.left.freq_hz,
        meas.left.mag_db,
        color=NORD["frost"],
        linewidth=1.6,
        label="Left",
    )
    ax.semilogx(
        meas.right.freq_hz,
        meas.right.mag_db,
        color=NORD["red"],
        linewidth=1.6,
        label="Right",
    )
    _style(
        ax, f"Room measurement: {meas.source.name}", "Frequency (Hz)", "Magnitude (dB)"
    )
    ax.set_xlim(F_MIN, F_MAX)
    leg = ax.legend(facecolor=NORD["bg"], edgecolor=NORD["grid"])
    for t in leg.get_texts():
        t.set_color(NORD["fg"])
    fig.tight_layout()
    fig.savefig(out, dpi=120, facecolor=NORD["bg"])
    plt.close(fig)


def plot_target(target: TargetEq, fs: float, out: Path) -> None:
    """
    Render a target EQ as a composite curve with the individual biquad bands overlaid.
    """
    grid = np.logspace(np.log10(F_MIN), np.log10(F_MAX), 4096)
    total = target_response_db(target, fs, grid)

    fig, ax = plt.subplots(figsize=(11, 5))
    # composite drawn first as a thick muted underlay, then individual
    # bands on top so the per-filter contribution is readable
    ax.semilogx(
        grid, total, linewidth=2.4, color=NORD["red"], label="composite", zorder=3
    )
    palette = [
        NORD["frost"],
        NORD["yellow"],
        NORD["green"],
        NORD["purple"],
        NORD["orange"],
        NORD["frost_deep"],
    ]
    for i, f in enumerate(target.filters):
        if not f.enabled:
            continue
        h = biquad_mag_db(f, fs, grid)
        ax.semilogx(
            grid,
            h,
            linewidth=1.3,
            alpha=0.85,
            color=palette[i % len(palette)],
            zorder=2,
            label=f"{f.type} {f.freq_hz:g} hz {f.gain_db:+g} db Q={f.q:g}",
        )
    _style(ax, f"Target EQ: {target.name}", "Frequency (Hz)", "Gain (dB)")
    ax.set_xlim(F_MIN, F_MAX)
    leg = ax.legend(facecolor=NORD["bg"], edgecolor=NORD["grid"], fontsize=9)
    for t in leg.get_texts():
        t.set_color(NORD["fg"])
    fig.tight_layout()
    fig.savefig(out, dpi=120, facecolor=NORD["bg"])
    plt.close(fig)
