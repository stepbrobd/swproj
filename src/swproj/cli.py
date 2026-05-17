from importlib.metadata import version as _pkg_version
from pathlib import Path

import click
from click.shell_completion import get_completion_class

from swproj.analysis import print_measurement_summary, print_target_summary
from swproj.parse import parse_swproj, parse_target_json
from swproj.plot import plot_measurement, plot_target

_PROG_NAME = "swproj"
_COMPLETE_VAR = "_SWPROJ_COMPLETE"
_CTX = {"help_option_names": ["-h", "--help"]}


@click.group(name=_PROG_NAME, context_settings=_CTX)
@click.version_option(_pkg_version("swproj"), "-v", "--version", prog_name=_PROG_NAME)
def cli() -> None:
    """
    Toolkit for Sonarworks SoundID measurements and target EQs.
    """


@cli.command()
@click.argument(
    "measurement_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="output png path (default: ./measurement.png)",
)
def measure(measurement_file: Path, output: Path | None) -> None:
    """
    Visualise a Sonarworks .swproj room measurement.
    """
    out = output if output is not None else Path.cwd() / "measurement.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    meas = parse_swproj(measurement_file)
    print_measurement_summary(meas)
    plot_measurement(meas, out)
    click.echo(f"wrote {out}")


@cli.command()
@click.argument(
    "target_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="output png path (default: ./target.png)",
)
@click.option(
    "--fs",
    type=float,
    default=48000.0,
    show_default=True,
    help="sample rate for biquad evaluation",
)
def target(target_file: Path, output: Path | None, fs: float) -> None:
    """
    Visualise a SoundID target EQ JSON.
    """
    out = output if output is not None else Path.cwd() / "target.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    tgt = parse_target_json(target_file)
    print_target_summary(tgt, fs=fs)
    plot_target(tgt, fs=fs, out=out)
    click.echo(f"wrote {out}")


@cli.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def comp(shell: str) -> None:
    """
    Print completion script for the chosen shell.

    Pipe the output into your shell's completion location, e.g.:
        swproj comp bash > ~/.local/share/bash-completion/completions/swproj
        swproj comp zsh  > ~/.zfunc/_swproj
        swproj comp fish > ~/.config/fish/completions/swproj.fish
    """
    cls = get_completion_class(shell)
    if cls is None:
        raise click.ClickException(f"Unsupported shell: {shell}")
    completion = cls(cli, {}, _PROG_NAME, _COMPLETE_VAR)
    click.echo(completion.source())
