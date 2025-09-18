import argparse
import contextlib
import re
import sys
from collections.abc import (  # noqa: TC003 — runtime import required (PEP 649)
    Callable,
    Generator,
)
from inspect import cleandoc
from pathlib import Path
from typing import NoReturn

import odoo.cli
import odoo.init  # noqa: F401 — side-effect import: Python version check + GC tuning
from odoo.modules import initialize_sys_path, load_script
from odoo.tools import config

COMMAND_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PROG_NAME = Path(sys.argv[0]).name
commands = {}
"""All loaded commands"""


def build_config_args(
    config_file: str | None = None,
    db_name: str | None = None,
    *,
    no_http: bool = True,
    extra_args: list[str] | None = None,
) -> list[str]:
    """
    Build argument list for config.parse_config().

    Args:
        config_file: Path to configuration file (-c)
        db_name: Database name (-d)
        no_http: Include --no-http flag (default True)
        extra_args: Additional arguments to append

    Returns:
        List of arguments ready for config.parse_config()
    """
    args = []
    if no_http:
        args.append("--no-http")
    if config_file:
        args.extend(["-c", config_file])
    if db_name:
        args.extend(["-d", db_name])
    if extra_args:
        args.extend(extra_args)
    return args


def get_single_database(
    db_names: list[str] | None,
    *,
    allow_none: bool = False,
    error_handler: Callable[[str], NoReturn] | None = None,
) -> str | None:
    """
    Validate and return a single database name from config.

    Args:
        db_names: List of database names (typically from config['db_name'])
        allow_none: If True, returns None when no database provided
        error_handler: Callable for error messages. Defaults to sys.exit().
                      For argparse integration, pass self.parser.error

    Returns:
        Single database name, or None if allow_none=True and no db provided

    Raises:
        SystemExit (via error_handler) if validation fails
    """
    if error_handler is None:
        error_handler = sys.exit

    if not db_names:
        if allow_none:
            return None
        error_handler(
            "No database specified. Use -d/--database or set db_name in config file."
        )

    if len(db_names) > 1:
        error_handler(
            "-d/--database/db_name has multiple databases, please provide a single one"
        )

    return db_names[0]


@contextlib.contextmanager
def odoo_env(
    db_name: str,
    *,
    readonly: bool = False,
    context: dict | None = None,
    uid: int | None = None,
    new_registry: bool = False,
) -> Generator:
    """
    Context manager for creating an Odoo Environment with proper cleanup.

    Args:
        db_name: Database name
        readonly: If True, use readonly cursor (no writes allowed)
        context: Custom context dict, defaults to {}
        uid: User ID, defaults to SUPERUSER_ID
        new_registry: If True, use Registry.new() instead of Registry()

    Yields:
        Odoo Environment instance

    Example:
        with odoo_env('mydb', readonly=True) as env:
            partners = env['res.partner'].search([])
    """
    # Lazy imports to maintain startup performance
    from odoo import SUPERUSER_ID
    from odoo.api import Environment
    from odoo.modules.registry import Registry

    if uid is None:
        uid = SUPERUSER_ID
    if context is None:
        context = {}

    registry_cls = Registry.new if new_registry else Registry
    with registry_cls(db_name).cursor(readonly=readonly) as cr:
        yield Environment(cr, uid, context)


class Command:
    name = None
    description = None
    epilog = None
    _parser = None  # NOTE: lazy init, not cached_property — allows subclass __init__ flexibility

    def __init_subclass__(cls):
        cls.name = cls.name or cls.__name__.lower()
        module = cls.__module__.rpartition(".")[2]
        if not cls.is_valid_name(cls.name):
            raise ValueError(
                f"Command name {cls.name!r} must match {COMMAND_NAME_RE.pattern!r}"
            )
        if cls.name != module:
            raise ValueError(
                f"Command name {cls.name!r} must match Module name {module!r}"
            )
        commands[cls.name] = cls

    @property
    def prog(self):
        return f"{PROG_NAME} [--addons-path=PATH,...] {self.name}"

    @property
    def parser(self):
        if not self._parser:
            self._parser = argparse.ArgumentParser(
                formatter_class=argparse.RawDescriptionHelpFormatter,
                prog=self.prog,
                description=cleandoc(self.description or self.__doc__ or ""),
                epilog=cleandoc(self.epilog or ""),
            )
        return self._parser

    @classmethod
    def is_valid_name(cls, name):
        return COMMAND_NAME_RE.match(name)

    def add_config_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add standard -c/--config and -d/--database arguments to parser.

        Args:
            parser: ArgumentParser or subparser to add arguments to
        """
        parser.add_argument(
            "-c",
            "--config",
            dest="config",
            help="use a specific configuration file",
        )
        parser.add_argument(
            "-d",
            "--database",
            dest="db_name",
            default=None,
            help="database name, connection details will be taken from the config file",
        )

    def require_single_database(
        self,
        parsed_args: argparse.Namespace,
        *,
        allow_none: bool = False,
    ) -> str | None:
        """
        Validate single database and update parsed_args.db_name.

        Uses self.parser.error() for error handling (argparse-style).

        Args:
            parsed_args: Namespace from argument parsing
            allow_none: If True, returns None when no database configured

        Returns:
            Database name (also set on parsed_args.db_name)

        Raises:
            SystemExit via parser.error() if validation fails
        """
        db_names = config["db_name"]
        if not db_names:
            if allow_none:
                return None
            self.parser.error("Please provide a single database in the config file")
        if len(db_names) > 1:
            self.parser.error("Please provide a single database in the config file")
        parsed_args.db_name = db_names[0]
        return db_names[0]


def load_internal_commands():
    """Load ``commands`` from ``odoo.cli``"""
    for path in odoo.cli.__path__:
        for module in Path(path).iterdir():
            if module.suffix != ".py":
                continue
            __import__(f"odoo.cli.{module.stem}")


def load_addons_commands(command=None):
    """
    Search the addons path for modules with a ``cli/{command}.py`` file.
    In case no command is provided, discover and load all the commands.
    """
    if command is None:
        command = "*"
    elif not Command.is_valid_name(command):
        return

    mapping = {}
    initialize_sys_path()
    for path in odoo.addons.__path__:
        for fullpath in Path(path).glob(f"*/cli/{command}.py"):
            if (found_command := fullpath.stem) and Command.is_valid_name(
                found_command
            ):
                # loading as odoo.cli and not odoo.addons.{module}.cli
                # so it doesn't load odoo.addons.{module}.__init__
                mapping[f"odoo.cli.{found_command}"] = fullpath

    for fq_name, fullpath in mapping.items():
        with contextlib.suppress(ImportError):
            load_script(fullpath, fq_name)


def find_command(name: str) -> Command | None:
    """Get command by name."""

    # built-in commands
    if command := commands.get(name):
        return command

    # import from odoo.cli
    with contextlib.suppress(ImportError):
        __import__(f"odoo.cli.{name}")
        return commands[name]

    # import from odoo.addons.*.cli
    load_addons_commands(command=name)
    return commands.get(name)


def main():
    args = sys.argv[1:]

    # The only shared option is '--addons-path=' needed to discover additional
    # commands from modules
    if (
        len(args) > 1
        and args[0].startswith("--addons-path=")
        and not args[1].startswith("-")
    ):
        # parse only the addons-path, do not setup the logger...
        config._parse_config([args[0]])
        args = args[1:]

    if args and not args[0].startswith("-"):
        # Command specified, search for it
        command_name = args[0]
        args = args[1:]
    elif "-h" in args or "--help" in args:
        # No command specified, but help is requested
        command_name = "help"
        args = [x for x in args if x not in ("-h", "--help")]
    else:
        # No command specified, default command used
        command_name = "server"

    if command := find_command(command_name):
        odoo.cli.COMMAND = command_name
        command().run(args)
    else:
        message = (
            f"Unknown command {command_name!r}.\n"
            f"Use '{PROG_NAME} --help' to see the list of available commands."
        )
        sys.exit(message)
