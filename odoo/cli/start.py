import os
import re
from collections.abc import Iterable
from pathlib import Path

import odoo.cli
from odoo.libs.debug_log import DebugLog
from odoo.modules.module import MANIFEST_NAMES, Manifest
from odoo.tools import config

from . import Command
from .server import run_server

_debug = DebugLog(__name__)


class Start(Command):
    description = "Quickly start the odoo server with default options"

    def _get_module_names_in_directory(self, path: str | Path) -> list[str]:
        base = Path(path)
        return [
            match.parent.name
            for mname in MANIFEST_NAMES
            for match in base.glob(f"*/{mname}")
        ]

    def __init__(self) -> None:
        super().__init__()
        self.parser.add_argument(
            "-p",
            "--path",
            default=None,
            help="Directory where your project's modules are stored "
            "(default: current directory, or $VIRTUAL_ENV when set). "
            "NOTE: `-p` is --path here, not the server's --http-port",
        )
        self.parser.add_argument(
            "-d",
            "--database",
            dest="db_name",
            default=None,
            help="database name (default: db_name from the config file, else "
            "the project directory name)",
        )

    def run(self, cmdargs: list[str]) -> None:
        config.parser.prog = self.prog
        args, _unknown = self.parser.parse_known_args(args=cmdargs)

        server_args = [v for i, v in enumerate(cmdargs) if not _is_path_arg(i, cmdargs)]
        _debug.logic(
            "cli.start.args_split",
            given=len(cmdargs),
            server=len(server_args),
            path_args=len(cmdargs) - len(server_args),
        )

        with _debug.perf("cli.start.preparse", args=len(server_args)):
            config._parse_config(server_args)

        project_path, db_name = self._get_project_path_and_db_name(
            args.path, args.db_name
        )

        mods = self._get_module_names_in_directory(project_path)
        _debug.pipeline(
            "cli.start.project_resolved",
            path=str(project_path),
            db=db_name,
            modules=len(mods),
            explicit_path=args.path is not None,
        )
        if mods and not _has_arg(server_args, "--addons-path"):
            addons_paths = _derive_addons_paths(
                project_path,
                bootstrap=odoo.cli.BOOTSTRAP_ADDONS_PATH,
                configured=config["addons_path"],
            )
            server_args.append(f"--addons-path={','.join(addons_paths)}")
            _debug.logic(
                "cli.start.addons_path_derived",
                paths=len(addons_paths),
                merged_bootstrap=bool(odoo.cli.BOOTSTRAP_ADDONS_PATH),
                merged_configured=len(config["addons_path"]),
            )

        if not args.db_name:
            server_args.extend(("-d", db_name))
            _debug.logic("cli.start.db_arg_derived", db=db_name)

        if not _has_arg(server_args, "--db-filter"):
            server_args.append(f"--db-filter=^{re.escape(db_name)}$")
            _debug.logic("cli.start.db_filter_derived", db=db_name)

        _debug.pipeline("cli.start.server_args", count=len(server_args))
        run_server(server_args)

    def _get_project_path_and_db_name(
        self, path: str | None, explicit_db_name: str | None
    ) -> tuple[Path, str]:
        if path is None:
            path = os.environ.get("VIRTUAL_ENV") or "."
            _debug.logic(
                "cli.start.path_source",
                source="virtual_env" if path != "." else "cwd",
            )
        else:
            _debug.logic("cli.start.path_source", source="explicit")
        project_path = Path(os.path.expandvars(path)).expanduser().resolve()
        if not project_path.is_dir():
            _debug.logic("cli.start.path_rejected", path=str(path), reason="not_dir")
            hint = (
                " (`-p` is --path here; the server's port option is --http-port)"
                if str(path).isdigit()
                else ""
            )
            self.parser.error(f"--path {path!r} is not a directory{hint}")

        db_name = None
        if is_path_in_module(project_path):
            db_name = project_path.name
            project_path = project_path.parent.resolve()
            _debug.logic("cli.start.path_in_module", module=db_name)

        configured = config["db_name"]
        _debug.logic(
            "cli.start.db_name_candidates",
            explicit=explicit_db_name,
            module=db_name,
            configured=len(configured) if configured else 0,
            fallback=project_path.name,
        )
        db_name = (
            explicit_db_name
            or db_name
            or (configured[0] if configured and len(configured) == 1 else None)
            or project_path.name
        )
        return project_path, db_name


def is_path_in_module(path: str | Path) -> bool:
    path = Path(path)
    return any(Manifest._from_path(str(p)) for p in (path, *path.parents))


# An explicit --addons-path on the command line replaces the configuration
# file's, so the project directory alone would drop every path the file
# names and leave the database's other modules unloadable. The project comes
# first among the non-bootstrap paths: it is what `start` was asked to run.
def _derive_addons_paths(
    project_path: Path, *, bootstrap: str | None, configured: Iterable[str]
) -> list[str]:
    user_paths = [p for p in (bootstrap or "").split(",") if p]
    return list(dict.fromkeys([*user_paths, str(project_path), *configured]))


def _is_path_arg(index: int, args: list[str]) -> bool:
    arg = args[index]
    if arg == "--path" or arg.startswith(("--path=", "-p")):
        return True
    return index > 0 and args[index - 1] in ("-p", "--path")


def _has_arg(cmdargs: list[str], name: str) -> bool:
    return any(arg == name or arg.startswith(f"{name}=") for arg in cmdargs)
