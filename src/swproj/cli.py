from importlib.metadata import version as _pkg_version

import click
from click.shell_completion import get_completion_class


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
