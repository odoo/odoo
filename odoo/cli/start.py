import os
import sys
from pathlib import Path

from odoo.modules.module import MANIFEST_NAMES, Manifest
from odoo.service.db import DatabaseExists, _create_empty_database
from odoo.tools import config

from . import Command
from .server import main


class Start(Command):
    """Quickly start the odoo server with default options"""

    def get_module_list(self, path):
        """Return module names found under ``path``."""
        base = Path(path)
        return [
            match.parent.name
            for mname in MANIFEST_NAMES
            for match in base.glob(f"*/{mname}")
        ]

    def run(self, cmdargs):
        config.parser.prog = self.prog
        self.parser.add_argument(
            "--path",
            default=".",
            help="Directory where your project's modules are stored (will autodetect from current dir)",
        )
        self.parser.add_argument(
            "-d",
            "--database",
            dest="db_name",
            default=None,
            help="Specify the database name (default to project's directory name",
        )

        args, _unknown = self.parser.parse_known_args(args=cmdargs)

        # When in a virtualenv, by default use its path rather than the cwd
        if args.path == "." and os.environ.get("VIRTUAL_ENV"):
            args.path = os.environ.get("VIRTUAL_ENV")
        project_path = Path(os.path.expandvars(args.path)).expanduser().resolve()
        db_name = None
        if is_path_in_module(project_path):
            # started in a module so we choose this module name for database
            db_name = project_path.name
            # go to the parent's directory of the module root
            project_path = project_path.parent.resolve()

        # check if one of the subfolders has at least one module
        mods = self.get_module_list(project_path)
        if mods and "--addons-path" not in cmdargs:
            cmdargs.append(f"--addons-path={project_path}")

        if not args.db_name:
            args.db_name = db_name or project_path.name
            cmdargs.extend(("-d", args.db_name))

        # TODO: forbid some database names ? eg template1, ...
        try:
            _create_empty_database(args.db_name)
            config["init"]["base"] = True
        except DatabaseExists:
            pass
        except Exception as e:
            sys.exit(f"Could not create database `{args.db_name}`. ({e})")

        if "--db-filter" not in cmdargs:
            cmdargs.append(f"--db-filter=^{args.db_name}$")

        # Remove --path /-p options from the command arguments
        def is_path_arg(index, args):
            return (
                args[index] == "-p"
                or args[index].startswith("--path")
                or (index > 0 and args[index - 1] in ["-p", "--path"])
            )

        cmdargs = [v for i, v in enumerate(cmdargs) if not is_path_arg(i, cmdargs)]

        main(cmdargs)


def is_path_in_module(path):
    """Check if ``path`` is inside an Odoo module directory."""
    path = Path(path)
    return any(Manifest._from_path(p) for p in (path, *path.parents))
