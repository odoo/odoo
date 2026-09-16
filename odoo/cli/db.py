import argparse
import sys
import tempfile
import textwrap
import urllib.parse
import zipfile
from argparse import RawTextHelpFormatter
from contextlib import ExitStack
from functools import partial
from pathlib import Path
from typing import NoReturn

import requests

from ..db import SYSTEM_DBS
from ..libs.debug_log import DebugLog
from ..service.db import (
    check_db_name,
    drop_database,
    dump_db,
    duplicate_database,
    exp_create_database,
    exp_db_exist,
    list_dbs,
    rename_database,
    restore_db,
)
from ..tools import config
from . import Command
from .command import check_db_not_maintenance
from .neutralize import neutralize_database_or_exit
from .server import report_configuration

_debug = DebugLog(__name__)

eprint = partial(print, file=sys.stderr, flush=True)

type _SubParsers = argparse._SubParsersAction[argparse.ArgumentParser]


class Db(Command):
    name = "db"
    description = """
        Command-line version of the database manager.

        Commands are all filestore-aware.
    """

    _CONNECTION_FLAGS = (
        ("-c", "--config"),
        ("-D", "--data-dir"),
        ("-r", "--db_user"),
        ("-w", "--db_password"),
        ("--pg_path",),
        ("--db_host",),
        ("--db_port",),
        ("--db_sslmode",),
    )

    _CONNECTION_HELP = {
        "--config": "use a specific configuration file",
        "--data-dir": "directory where to store Odoo data",
        "--db_user": "database user",
        "--db_password": "database password",
        "--pg_path": "directory holding the PostgreSQL client binaries",
        "--db_host": "database server host",
        "--db_port": "database server port",
        "--db_sslmode": "SSL mode for the database connection",
    }

    @classmethod
    def _add_connection_flags(
        cls, p: argparse.ArgumentParser, *, on_subparser: bool = False
    ) -> None:
        for flags in cls._CONNECTION_FLAGS:
            help_text = cls._CONNECTION_HELP.get(flags[-1])
            if on_subparser:
                p.add_argument(*flags, default=argparse.SUPPRESS, help=help_text)
            else:
                p.add_argument(*flags, help=help_text)

    @classmethod
    def _get_connection_flags_by_dest(cls) -> dict[str, str]:
        dest_flags = {}
        for flags in cls._CONNECTION_FLAGS:
            long_flag = flags[-1]
            dest_flags[long_flag.lstrip("-").replace("-", "_")] = long_flag
        return dest_flags

    def _exit_missing_subcommand(self, _args: argparse.Namespace) -> NoReturn:
        _debug.logic("cli.db.rejected", reason="no_subcommand")
        self.parser.print_help(sys.stderr)
        sys.exit(2)

    def __init__(self) -> None:
        super().__init__()
        parser = self.parser
        self._add_connection_flags(parser)
        parser.set_defaults(func=self._exit_missing_subcommand)

        subs = parser.add_subparsers()
        subparsers = [
            build(subs)
            for build in (
                self._add_init_parser,
                self._add_load_parser,
                self._add_dump_parser,
                self._add_duplicate_parser,
                self._add_rename_parser,
                self._add_drop_parser,
                self._add_list_parser,
            )
        ]
        for sub in subparsers:
            self._add_connection_flags(sub, on_subparser=True)

    def _add_init_parser(self, subs: _SubParsers) -> argparse.ArgumentParser:
        init = subs.add_parser(
            "init",
            help="Create and initialize a database",
            description="Create an empty database and install the minimum required modules",
            formatter_class=RawTextHelpFormatter,
        )
        init.set_defaults(func=self.init)
        init.add_argument(
            "database",
            help="database to create",
        )
        init.add_argument(
            "--with-demo",
            action="store_true",
            help="install demo data in the new database",
        )
        init.add_argument(
            "--force",
            action="store_true",
            help="delete database if exists",
        )
        init.add_argument(
            "--language",
            default="en_US",
            help="default language for the instance, default 'en_US'",
        )
        init.add_argument(
            "--username",
            default="admin",
            help="admin username, default 'admin'",
        )
        init.add_argument(
            "--password",
            default="admin",
            help="admin password, default 'admin'",
        )
        init.add_argument(
            "--country",
            help="country to be set on the main company",
        )
        init.epilog = textwrap.dedent("""\

                Database initialization will install the minimum required modules.
                To install more modules, use the `module install` command.
                For more info:

                $ odoo-bin module install --help
        """)
        return init

    def _add_load_parser(self, subs: _SubParsers) -> argparse.ArgumentParser:
        load = subs.add_parser(
            "load",
            help="Load a dump file.",
            description="Loads a dump file into odoo, dump file can be a URL. "
            "If `database` is provided, uses that as the database name. "
            "Otherwise uses the dump file name without extension.",
        )
        load.set_defaults(func=self.load)
        load.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="delete `database` database before loading if it exists",
        )
        load.add_argument(
            "-n",
            "--neutralize",
            action="store_true",
            help="neutralize the database after restore",
        )
        load.add_argument(
            "--move",
            dest="copy",
            action="store_const",
            default=True,
            const=False,
            help="restore as a moved database, keeping its UUID instead of generating a new one",
        )
        load.add_argument(
            "database",
            nargs="?",
            help="database to create, defaults to dump file's name (without extension)",
        )
        load.add_argument(
            "dump_file",
            help="zip or pg_dump file to load",
        )
        return load

    def _add_dump_parser(self, subs: _SubParsers) -> argparse.ArgumentParser:
        dump = subs.add_parser(
            "dump",
            help="Create a dump with filestore.",
            description="Creates a dump file. The dump is always in zip format "
            "(with filestore), to get pg_dump format, use "
            "dump_format argument.",
        )
        dump.set_defaults(func=self.dump)
        dump.add_argument("database", help="database to dump")
        dump.add_argument(
            "dump_path",
            nargs="?",
            default="-",
            help="path to dump to; omit or pass `-` to dump to stdout",
        )
        dump.add_argument(
            "--format",
            dest="dump_format",
            choices=("zip", "dump"),
            default="zip",
            help="format to dump in (default: `zip`).\n"
            "Supported formats: `zip`, `dump` (pg_dump format).",
        )
        dump.add_argument(
            "--no-filestore",
            action="store_const",
            dest="filestore",
            default=True,
            const=False,
            help="dump the zip without the filestore (default: included)",
        )
        return dump

    def _add_duplicate_parser(self, subs: _SubParsers) -> argparse.ArgumentParser:
        duplicate = subs.add_parser(
            "duplicate",
            help="Duplicate a database including filestore.",
        )
        duplicate.set_defaults(func=self.duplicate)
        duplicate.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="delete `target` database before copying if it exists",
        )
        duplicate.add_argument(
            "-n",
            "--neutralize",
            action="store_true",
            help="neutralize the target database after duplicate",
        )
        duplicate.add_argument("source")
        duplicate.add_argument(
            "target",
            help="database to copy `source` to, must not exist unless `-f` is specified in which case it will be dropped first",
        )
        return duplicate

    def _add_rename_parser(self, subs: _SubParsers) -> argparse.ArgumentParser:
        rename = subs.add_parser(
            "rename", help="Rename a database including filestore."
        )
        rename.set_defaults(func=self.rename)
        rename.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="delete `target` database before renaming if it exists",
        )
        rename.add_argument(
            "-n",
            "--neutralize",
            action="store_true",
            help="neutralize the database after rename",
        )
        rename.add_argument("source")
        rename.add_argument(
            "target",
            help="database to rename `source` to, must not exist unless `-f` is specified, in which case it will be dropped first",
        )
        return rename

    def _add_drop_parser(self, subs: _SubParsers) -> argparse.ArgumentParser:
        drop = subs.add_parser("drop", help="Delete a database including filestore")
        drop.set_defaults(func=self.drop)
        drop.add_argument("database", help="database to delete")
        return drop

    def _add_list_parser(self, subs: _SubParsers) -> argparse.ArgumentParser:
        list_parser = subs.add_parser(
            "list",
            help="List databases visible to this Odoo instance",
            description="Lists the databases this instance can see, one per "
            "line. db_name from the config constrains the result the same "
            "way it does for the database-manager UI. dbfilter does NOT: "
            "it is a regex evaluated against an HTTP request host, which "
            "has no meaning outside a web request, so this command lists "
            "every database dbfilter would otherwise narrow down.",
        )
        list_parser.set_defaults(func=self.list_databases)
        return list_parser

    def run(self, cmdargs: list[str]) -> None:
        args, unknown = self.parser.parse_known_args(cmdargs)

        dest_flags = self._get_connection_flags_by_dest()
        config_args: list[str] = []
        for key, value in vars(args).items():
            if value is None or key not in dest_flags:
                continue
            config_args.extend([dest_flags[key], value])
        config.parse_config([*config_args, *unknown], setup_logging=True)
        config["list_db"] = True
        _debug.pipeline(
            "cli.db.config_parsed",
            connection_flags=len(config_args) // 2,
            forwarded=len(unknown),
        )
        report_configuration()

        subcommand = getattr(args.func, "__name__", None)
        _debug.lifecycle(
            "cli.db",
            subcommand=subcommand,
            database=getattr(args, "database", None),
        )
        args.func(args)
        _debug.lifecycle("cli.db.done", subcommand=subcommand)

    def init(self, args: argparse.Namespace) -> None:
        self._check_target_free(args.database, force=args.force)
        self._drop_database_if_exists(args.database)
        _debug.lifecycle(
            "cli.db.init",
            db=args.database,
            demo=args.with_demo,
            lang=args.language,
            country=args.country,
        )
        with _debug.perf("cli.db.create", db=args.database, demo=args.with_demo):
            exp_create_database(
                db_name=args.database,
                demo=args.with_demo,
                lang=args.language,
                login=args.username,
                user_password=args.password,
                country_code=args.country,
                phone=None,
            )
        _debug.lifecycle("cli.db.initialized", db=args.database, login=args.username)

    def load(self, args: argparse.Namespace) -> None:
        db_name = args.database or Path(args.dump_file).stem
        try:
            check_db_name(db_name)
        except ValueError as e:
            _debug.logic("cli.db.load.rejected", db=db_name, reason="invalid_name")
            sys.exit(f"{e}")
        self._check_target_free(db_name, force=args.force)

        url = urllib.parse.urlparse(args.dump_file)
        _debug.logic(
            "cli.db.load.source",
            db=db_name,
            kind="url" if url.scheme else "file",
            named=bool(args.database),
        )
        with ExitStack() as stack:
            if url.scheme:
                eprint(f"Fetching {args.dump_file}...", end="")
                r = stack.enter_context(
                    requests.get(args.dump_file, timeout=(10, None), stream=True)
                )
                if not r.ok:
                    _debug.logic(
                        "cli.db.load.fetch_failed",
                        status=r.status_code,
                        reason=r.reason,
                    )
                    sys.exit(f" unable to fetch {args.dump_file}: {r.reason}")
                downloaded = stack.enter_context(
                    tempfile.SpooledTemporaryFile(max_size=256 * 1024 * 1024)
                )
                with _debug.perf("cli.db.load.fetch", status=r.status_code) as span:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        downloaded.write(chunk)
                    span.set(bytes=downloaded.tell())
                downloaded.seek(0)
                dump_file = downloaded
                eprint(" done")
            else:
                eprint(f"Restoring {args.dump_file}...")
                dump_file = args.dump_file

            if not zipfile.is_zipfile(dump_file):
                _debug.logic("cli.db.load.rejected", db=db_name, reason="not_zip")
                sys.exit(
                    "Not a zipped dump file, use `pg_restore` to restore raw dumps,"
                    " and `psql` to execute sql dumps or scripts."
                )

            if args.force:
                self._drop_database_if_exists(db_name)
            _debug.pipeline(
                "cli.db.load.restore",
                db=db_name,
                source="url" if url.scheme else "file",
                copy=args.copy,
                neutralize=args.neutralize,
            )
            with _debug.perf(
                "cli.db.restore", db=db_name, copy=args.copy, neutralize=args.neutralize
            ):
                restore_db(
                    db=db_name,
                    dump_file=dump_file,
                    copy=args.copy,
                    neutralize_database=args.neutralize,
                )
            _debug.lifecycle(
                "cli.db.loaded",
                db=db_name,
                moved=not args.copy,
                neutralized=args.neutralize,
            )

    def dump(self, args: argparse.Namespace) -> None:
        if args.database in SYSTEM_DBS:
            _debug.logic("cli.db.dump.rejected", db=args.database, reason="system_db")
            sys.exit(f"Refusing to dump system database {args.database}.")
        self._check_source_exists(args.database)
        if args.dump_path == "-":
            with _debug.perf(
                "cli.db.dump",
                db=args.database,
                format=args.dump_format,
                filestore=args.filestore,
                to="stdout",
            ):
                dump_db(
                    args.database, sys.stdout.buffer, args.dump_format, args.filestore
                )
        else:
            destination = Path(args.dump_path)
            if not destination.parent.is_dir():
                _debug.logic(
                    "cli.db.dump.rejected", db=args.database, reason="no_parent_dir"
                )
                sys.exit(
                    f"Cannot write {args.dump_path}: {destination.parent} is not "
                    "a directory."
                )
            try:
                with destination.open("wb") as f:
                    with _debug.perf(
                        "cli.db.dump",
                        db=args.database,
                        format=args.dump_format,
                        filestore=args.filestore,
                        to=str(destination),
                    ) as span:
                        dump_db(args.database, f, args.dump_format, args.filestore)
                        span.set(bytes=f.tell())
            except BaseException:
                _debug.logic(
                    "cli.db.dump.aborted", db=args.database, to=str(destination)
                )
                destination.unlink(missing_ok=True)
                raise
            _debug.lifecycle(
                "cli.db.dumped",
                db=args.database,
                to=str(destination),
                format=args.dump_format,
            )

    def duplicate(self, args: argparse.Namespace) -> None:
        self._check_source_not_target(args.source, args.target)
        self._check_target_free(args.target, force=args.force)
        self._check_source_exists(args.source)
        self._drop_database_if_exists(args.target)
        with _debug.perf(
            "cli.db.duplicate",
            source=args.source,
            target=args.target,
            neutralize=args.neutralize,
        ):
            duplicate_database(
                args.source, args.target, neutralize_database=args.neutralize
            )
        _debug.lifecycle(
            "cli.db.duplicated",
            source=args.source,
            target=args.target,
            neutralized=args.neutralize,
        )

    def rename(self, args: argparse.Namespace) -> None:
        self._check_source_not_target(args.source, args.target)
        check_db_not_maintenance(args.source)
        self._check_target_free(args.target, force=args.force)
        self._check_source_exists(args.source)
        self._drop_database_if_exists(args.target)
        with _debug.perf("cli.db.rename", source=args.source, target=args.target):
            rename_database(args.source, args.target)
        _debug.lifecycle("cli.db.renamed", source=args.source, target=args.target)
        if args.neutralize:
            neutralize_database_or_exit(args.target)
            _debug.lifecycle("cli.db.neutralized", db=args.target)

    def drop(self, args: argparse.Namespace) -> None:
        check_db_not_maintenance(args.database)
        _debug.lifecycle("cli.db.drop", db=args.database)
        if not drop_database(args.database):
            _debug.logic("cli.db.drop.missing", db=args.database)
            sys.exit(f"Database {args.database} does not exist.")
        _debug.lifecycle("cli.db.dropped", db=args.database)

    def list_databases(self, _args: argparse.Namespace) -> None:
        with _debug.perf("cli.db.list") as span:
            db_names = list_dbs(force=True)
            span.set(count=len(db_names))
        for db_name in db_names:
            print(db_name)

    def _check_target_free(self, target: str, *, force: bool) -> None:
        check_db_not_maintenance(target)
        if force:
            _debug.logic("cli.db.target_check_skipped", target=target, reason="force")
            return
        if exp_db_exist(target):
            _debug.logic("cli.db.target_exists", target=target, force=False)
            sys.exit(
                f"Target database {target} exists, aborting.\n\n"
                f"\tuse `--force` to delete the existing database anyway."
            )
        _debug.logic("cli.db.target_free", target=target)

    def _check_source_exists(self, source: str) -> None:
        if not exp_db_exist(source):
            _debug.logic("cli.db.source_missing", source=source)
            sys.exit(f"Source database {source} does not exist.")

    def _check_source_not_target(self, source: str, target: str) -> None:
        if source == target:
            _debug.logic("cli.db.source_is_target", db=source)
            sys.exit(f"Source and target database are both {source!r}: aborting.")

    def _drop_database_if_exists(self, target: str) -> None:
        check_db_not_maintenance(target)
        if not exp_db_exist(target):
            _debug.logic("cli.db.existing_drop_skipped", db=target, reason="absent")
            return
        _debug.lifecycle("cli.db.existing_dropped", db=target)
        with _debug.perf("cli.db.existing_drop", db=target):
            drop_database(target)
