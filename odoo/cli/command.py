import argparse
import contextlib
import logging
import re
import sys
from collections.abc import Callable, Generator
from inspect import cleandoc
from pathlib import Path
from typing import Literal, NoReturn, overload

import odoo.cli
import odoo.init  # noqa: F401  imported for the bootstrap side effect (gc, monkeypatches)
from odoo.db import is_maintenance_db
from odoo.libs.debug_log import DebugLog
from odoo.modules import initialize_sys_path, load_script
from odoo.tools import config

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

COMMAND_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*\Z")
PROG_NAME = Path(sys.argv[0]).name
DEFAULT_COMMAND = "server"
MAINTENANCE_DB_MESSAGE = "Refusing to operate on system or template database {db_name}."
commands: dict[str, type[Command]] = {}


def prepare_config_args(
    config_file: str | None = None,
    db_name: str | None = None,
    *,
    no_http: bool = True,
    extra_args: list[str] | None = None,
) -> list[str]:
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
    if error_handler is None:
        error_handler = sys.exit

    if not db_names:
        if allow_none:
            _debug.logic("cli.database.selected", db=None, reason="none_allowed")
            return None
        _debug.logic("cli.database.rejected", reason="none")
        error_handler(
            "No database specified. Use -d/--database or set db_name in the config file."
        )
        return None

    if len(db_names) > 1:
        _debug.logic("cli.database.rejected", reason="multiple", count=len(db_names))
        error_handler(
            f"Multiple databases configured ({db_names}); "
            "please provide a single one via -d/--database."
        )
        return None

    db_name = db_names[0]
    if is_maintenance_db(db_name):
        _debug.logic("cli.database.rejected", reason="maintenance", db=db_name)
        error_handler(MAINTENANCE_DB_MESSAGE.format(db_name=db_name))
        return None

    _debug.logic("cli.database.selected", db=db_name, reason="single")
    return db_name


def check_db_not_maintenance(
    db_name: str,
    *,
    error_handler: Callable[[str], NoReturn] | None = None,
) -> None:
    if error_handler is None:
        error_handler = sys.exit
    if is_maintenance_db(db_name):
        _debug.logic("cli.database.rejected", reason="maintenance", db=db_name)
        error_handler(MAINTENANCE_DB_MESSAGE.format(db_name=db_name))


@contextlib.contextmanager
def open_environment(
    db_name: str,
    *,
    readonly: bool = False,
    context: dict | None = None,
    uid: int | None = None,
    new_registry: bool = False,
) -> Generator:
    from odoo import SUPERUSER_ID
    from odoo.api import Environment
    from odoo.modules.registry import Registry

    if uid is None:
        uid = SUPERUSER_ID
    if context is None:
        context = {}

    registry_cls = Registry.new if new_registry else Registry
    _debug.lifecycle(
        "cli.open_environment",
        db=db_name,
        readonly=readonly,
        uid=uid,
        new_registry=new_registry,
    )
    with _debug.perf("cli.registry", db=db_name, new_registry=new_registry):
        registry = registry_cls(db_name)
    with registry.cursor(readonly=readonly) as cr:
        env = Environment(cr, uid, context)
        env.transaction.default_env = env
        with _debug.perf("cli.environment", cr=cr, db=db_name, readonly=readonly):
            yield env
        _debug.lifecycle(
            "cli.environment.closing",
            db=db_name,
            readonly=readonly,
            models=len(registry.models),
        )


class Command:
    name: str | None = None
    description: str | None = None
    epilog: str | None = None

    def __init__(self) -> None:
        self._parser: argparse.ArgumentParser | None = None

    def run(self, args: list[str]) -> None:
        raise NotImplementedError(
            f"{type(self).__qualname__} must override `run(self, args)`"
        )

    def __init_subclass__(cls, register: bool = True) -> None:
        if not register:
            return
        cls.name = cls.name or cls.__name__.lower()
        module = cls.__module__.rpartition(".")[2]
        if not cls.is_valid_name(cls.name):
            _debug.logic(
                "cli.command.registration_rejected",
                name=cls.name,
                reason="invalid_name",
            )
            raise ValueError(
                f"Command name {cls.name!r} must match {COMMAND_NAME_RE.pattern!r}"
            )
        if cls.name != module:
            _debug.logic(
                "cli.command.registration_rejected",
                name=cls.name,
                module=module,
                reason="module_mismatch",
            )
            raise ValueError(
                f"Command name {cls.name!r} must match Module name {module!r}"
            )
        if cls.run is Command.run:
            _debug.logic(
                "cli.command.registration_rejected", name=cls.name, reason="no_run"
            )
            raise TypeError(
                f"Command subclass {cls.__qualname__!r} must override "
                "`run(self, args: list[str]) -> None`"
            )
        if cls.name in commands:
            _debug.logic(
                "cli.command.redefined",
                name=cls.name,
                was=commands[cls.name].__module__,
                now=cls.__module__,
            )
            _logger.warning(
                "Command %r redefined: was %s, now %s (second registration wins)",
                cls.name,
                commands[cls.name].__module__,
                cls.__module__,
            )
        commands[cls.name] = cls
        _debug.lifecycle("cli.command.registered", name=cls.name, module=cls.__module__)

    @property
    def prog(self) -> str:
        return f"{PROG_NAME} [--addons-path=PATH,...] {self.name}"

    @property
    def parser(self) -> argparse.ArgumentParser:
        if self._parser is None:
            self._parser = argparse.ArgumentParser(
                formatter_class=argparse.RawDescriptionHelpFormatter,
                prog=self.prog,
                description=cleandoc(self.description or self.__doc__ or ""),
                epilog=cleandoc(self.epilog or ""),
            )
            _debug.lifecycle("cli.parser.built", command=self.name)
        return self._parser

    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        return COMMAND_NAME_RE.match(name) is not None


class DatabaseCommand(Command, register=False):
    def add_config_arguments(
        self, parser: argparse.ArgumentParser, *, on_subparser: bool = False
    ) -> None:
        extra = {"default": argparse.SUPPRESS} if on_subparser else {"default": None}
        parser.add_argument(
            "-c",
            "--config",
            dest="config",
            help="use a specific configuration file",
            **extra,
        )
        parser.add_argument(
            "-d",
            "--database",
            dest="db_name",
            help="database name, connection details will be taken from the config file",
            **extra,
        )
        parser.add_argument(
            "-D",
            "--data-dir",
            dest="data_dir",
            help="directory where to store Odoo data",
            **extra,
        )

    def parse_args(self, args: list[str]) -> tuple[argparse.Namespace, list[str]]:
        parsed, unknown = self.parser.parse_known_args(args)
        _debug.logic(
            "cli.args.parsed",
            command=self.name,
            given=len(args),
            forwarded=len(unknown),
            subcommand=getattr(parsed, "subcommand", None),
        )
        return parsed, unknown

    @overload
    def bootstrap_config(
        self,
        parsed_args: argparse.Namespace,
        *,
        allow_none: Literal[False] = False,
        extra_args: list[str] | None = None,
    ) -> str: ...

    @overload
    def bootstrap_config(
        self,
        parsed_args: argparse.Namespace,
        *,
        allow_none: Literal[True],
        extra_args: list[str] | None = None,
    ) -> str | None: ...

    def bootstrap_config(
        self,
        parsed_args: argparse.Namespace,
        *,
        allow_none: bool = False,
        extra_args: list[str] | None = None,
    ) -> str | None:
        forwarded = list(extra_args or [])
        if getattr(parsed_args, "data_dir", None):
            forwarded = ["-D", parsed_args.data_dir, *forwarded]
        config_args = prepare_config_args(
            parsed_args.config,
            parsed_args.db_name,
            extra_args=forwarded or None,
        )
        with _debug.perf("cli.config.parse", command=self.name, args=len(config_args)):
            config.parse_config(config_args, setup_logging=True)
        _debug.pipeline(
            "cli.config.bootstrapped",
            command=self.name,
            config_file=bool(parsed_args.config),
            db=parsed_args.db_name,
            data_dir=bool(getattr(parsed_args, "data_dir", None)),
            forwarded=len(forwarded),
        )
        return self.get_configured_database(parsed_args, allow_none=allow_none)

    def get_configured_database(
        self,
        parsed_args: argparse.Namespace,
        *,
        allow_none: bool = False,
    ) -> str | None:
        db_name = get_single_database(
            config["db_name"],
            allow_none=allow_none,
            error_handler=self.parser.error,
        )
        if db_name is not None:
            parsed_args.db_name = db_name
        return db_name


def load_internal_commands() -> None:
    before = len(commands)
    with _debug.perf("cli.commands.internal_load") as span:
        imported = 0  # debuglog
        for path in odoo.cli.__path__:
            for module in Path(path).iterdir():
                if module.suffix != ".py" or module.stem.startswith("_"):
                    continue
                __import__(f"odoo.cli.{module.stem}")
                imported += 1  # debuglog
        span.set(imported=imported)
    _debug.pipeline(
        "cli.commands.internal_loaded",
        registered=len(commands),
        added=len(commands) - before,
    )


def load_addons_commands(command: str | None = None) -> None:
    if command is None:
        command = "*"
    elif not Command.is_valid_name(command):
        _debug.logic(
            "cli.commands.addons_skipped", command=command, reason="invalid_name"
        )
        return

    mapping: dict[str, Path] = {}
    initialize_sys_path()
    for path in odoo.addons.__path__:
        for fullpath in sorted(Path(path).glob(f"*/cli/{command}.py")):
            found_command = fullpath.stem
            if not Command.is_valid_name(found_command):
                _debug.logic(
                    "cli.commands.addon_skipped",
                    path=str(fullpath),
                    reason="invalid_name",
                )
                continue
            fq_name = f"odoo.cli.{found_command}"
            if fq_name in mapping:
                # addons_path order is priority, as for modules: the first
                # path that defines the command keeps it.
                _debug.logic(
                    "cli.commands.addon_shadowed",
                    command=found_command,
                    winner=str(mapping[fq_name]),
                    loser=str(fullpath),
                )
                _logger.warning(
                    "Addon CLI command %r is defined in multiple addons: "
                    "%s shadows %s (addons_path order)",
                    found_command,
                    mapping[fq_name],
                    fullpath,
                )
                continue
            mapping[fq_name] = fullpath
    _debug.pipeline(
        "cli.commands.addons_discovered",
        command=command,
        found=len(mapping),
        addons_paths=len(odoo.addons.__path__),
    )

    for fq_name, fullpath in mapping.items():
        try:
            with _debug.perf(
                "cli.commands.addon_load", name=fq_name, path=str(fullpath)
            ):
                load_script(str(fullpath), fq_name)
        except ImportError as e:
            _debug.logic(
                "cli.commands.addon_load_failed", name=fq_name, reason="import"
            )
            _logger.debug("Could not load CLI command %s: %s", fq_name, e)
        except Exception as e:
            _debug.logic(
                "cli.commands.addon_load_failed", name=fq_name, reason=type(e).__name__
            )
            _logger.warning("Failed to load CLI command %s: %s", fq_name, e)


def get_cli_command(name: str) -> type[Command] | None:
    if not Command.is_valid_name(name):
        _debug.logic(
            "cli.command.resolved", name=name, found=False, reason="invalid_name"
        )
        return None

    source = "registered"
    if name not in commands:
        expected_module = f"odoo.cli.{name}"
        try:
            with _debug.perf("cli.command.internal_import", name=name):
                __import__(expected_module)
            source = "internal"
        except ModuleNotFoundError as e:
            if e.name != expected_module:
                raise
            _debug.logic("cli.command.internal_missing", name=name)
            source = "addon"
        load_addons_commands(command=name)

    _debug.logic(
        "cli.command.resolved", name=name, found=name in commands, source=source
    )
    return commands.get(name)


def prepare_bootstrap_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--addons-path", default=None)
    return parser


def _select_run_mode() -> None:
    if odoo.evented or not (len(sys.argv) > 1 and sys.argv[1] == "evented"):
        return
    sys.argv.remove("evented")
    odoo.evented = True
    _debug.lifecycle("cli.evented_mode", enabled=True)


def main() -> None:
    _select_run_mode()
    args = sys.argv[1:]

    boot_parser = prepare_bootstrap_parser()
    bootstrap, args = boot_parser.parse_known_args(args)
    odoo.cli.BOOTSTRAP_ADDONS_PATH = bootstrap.addons_path
    if bootstrap.addons_path is not None:
        config._parse_config([f"--addons-path={bootstrap.addons_path}"])

    if args and not args[0].startswith("-"):
        command_name = args[0]
        args = args[1:]
        chosen_by = "positional"
    elif args and args[0] in ("-h", "--help"):
        command_name = "help"
        args = args[1:]
        chosen_by = "help_flag"
    else:
        command_name = DEFAULT_COMMAND
        chosen_by = "default"

    odoo.cli.COMMAND = command_name
    _debug.lifecycle(
        "cli.command",
        command=command_name,
        chosen_by=chosen_by,
        args=len(args),
        addons_path=bootstrap.addons_path is not None,
        evented=odoo.evented,
    )
    if command := get_cli_command(command_name):
        with _debug.perf("cli.command.run", command=command_name):
            command().run(args)
        _debug.lifecycle("cli.command.done", command=command_name)
    else:
        _debug.logic("cli.command.unknown", command=command_name)
        sys.exit(
            f"Unknown command {command_name!r}.\n"
            f"Use '{PROG_NAME} --help' to see the list of available commands."
        )
