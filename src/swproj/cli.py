from importlib.metadata import version as _pkg_version
from pathlib import Path

import click
from click.shell_completion import get_completion_class

from swproj.analysis import print_measurement_summary, print_target_summary
from swproj.camilladsp import build_config, emit_yaml
from swproj.parse import parse_swproj, parse_target_json
from swproj.plot import plot_measurement, plot_target
from swproj.types import FilterPhase

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
    help="Output PNG path (default: ./measurement.png).",
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
    help="Output PNG path (default: ./target.png).",
)
@click.option(
    "-r",
    "--rate",
    type=click.IntRange(8000, 384000),
    default=48000,
    show_default=True,
    help="Sample rate (Hz) for biquad evaluation.",
)
def target(target_file: Path, output: Path | None, rate: int) -> None:
    """
    Visualise a SoundID target EQ JSON.
    """
    out = output if output is not None else Path.cwd() / "target.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    tgt = parse_target_json(target_file)
    print_target_summary(tgt, fs=rate)
    plot_target(tgt, fs=rate, out=out)
    click.echo(f"wrote {out}")


@cli.command()
@click.option(
    "-m",
    "--measure",
    "measure_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Room measurement (.swproj).",
)
@click.option(
    "-t",
    "--target",
    "target_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Target EQ (.json).",
)
@click.option(
    "-f",
    "--filter",
    "phase",
    type=click.Choice(FilterPhase, case_sensitive=False),
    default=FilterPhase.LINEAR,
    show_default="linear",
    help="Phase character of the room-correction FIR.",
)
@click.option(
    "-r",
    "--rate",
    type=click.IntRange(8000, 384000),
    default=48000,
    show_default=True,
    help="Sample rate (Hz).",
)
@click.option(
    "-n",
    "--taps",
    type=click.IntRange(256),
    default=8192,
    show_default=True,
    help="FIR length (samples).",
)
@click.option(
    "-b",
    "--max-boost",
    type=click.FloatRange(0.0),
    default=12.0,
    show_default=True,
    help="Cap on inverse magnitude (dB).",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write YAML to file (default: stdout).",
)
def camilladsp(
    measure_file: Path | None,
    target_file: Path | None,
    phase: FilterPhase,
    rate: int,
    taps: int,
    max_boost: float,
    output: Path | None,
) -> None:
    """
    Emit CamillaDSP filters+pipeline YAML built from a SoundID measurement and/or target EQ.
    """
    if measure_file is None and target_file is None:
        raise click.UsageError(
            "at least one of -m/--measure or -t/--target is required"
        )

    measurement = parse_swproj(measure_file) if measure_file is not None else None
    target = parse_target_json(target_file) if target_file is not None else None

    config = build_config(
        measurement=measurement,
        target=target,
        rate=rate,
        taps=taps,
        max_boost_db=max_boost,
        phase=phase,
    )
    text = emit_yaml(config)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
        click.echo(f"wrote {output}", err=True)
    else:
        click.echo(text, nl=False)


@cli.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def comp(shell: str) -> None:
    """
    Print completion script for the chosen shell.

    \b
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
