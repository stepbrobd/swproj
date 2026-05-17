from typing import Final

import matplotlib
from matplotlib.axes import Axes

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
