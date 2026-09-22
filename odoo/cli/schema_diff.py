import contextlib
import logging
import re
import sys
import typing
from collections import Counter
from unittest.mock import patch

from odoo.db import BaseCursor
from odoo.libs.debug_log import DebugLog

from . import DatabaseCommand

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_DDL = re.compile(r"^\s*(ALTER|CREATE|DROP|COMMENT ON|TRUNCATE)\b", re.IGNORECASE)
_META_DML = re.compile(
    r"^\s*(INSERT INTO|UPDATE|DELETE FROM)\s+\"?(ir_[a-z_]+|res_groups|res_users)\"?",
    re.IGNORECASE,
)
_MIGRATION = re.compile(r"^module (\S+): Running migration (\S+) (\S+)$")


class _Recorder:
    def __init__(self) -> None:
        self.ddl: list[str] = []
        self.meta: Counter[str] = Counter()
        self.migrations: list[tuple[str, str, str]] = []

    def record(self, query: typing.Any) -> None:
        code = query if isinstance(query, str) else getattr(query, "code", None)
        if not isinstance(code, str):
            return
        text = " ".join(code.split())
        if _DDL.match(text):
            self.ddl.append(text)
        elif match := _META_DML.match(text):
            self.meta[f"{match.group(1).upper()} {match.group(2)}"] += 1


class _MigrationLog(logging.Handler):
    def __init__(self, recorder: _Recorder) -> None:
        super().__init__(logging.INFO)
        self.recorder = recorder

    def emit(self, record: logging.LogRecord) -> None:
        if match := _MIGRATION.match(record.getMessage()):
            module, version, script = match.groups()
            self.recorder.migrations.append((module, version, script))


class SchemaDiff(DatabaseCommand):
    name = "schema_diff"
    description = (
        "Run an install or upgrade in a transaction that is rolled back, and "
        "print the DDL and migrations it would have committed"
    )

    def __init__(self) -> None:
        super().__init__()
        self.add_config_arguments(self.parser)
        self.parser.add_argument(
            "-u",
            "--update",
            dest="update",
            default="",
            help="comma-separated modules to upgrade",
        )
        self.parser.add_argument(
            "-i",
            "--init",
            dest="init",
            default="",
            help="comma-separated modules to install",
        )
        self.parser.add_argument(
            "--all",
            dest="show_all",
            action="store_true",
            help="print every DDL statement; the default folds identical shapes",
        )

    def run(self, cmdargs: list[str]) -> None:
        parsed_args, unknown = self.parse_args(cmdargs)
        db_name = self.bootstrap_config(parsed_args, extra_args=unknown)
        upgrade = [m for m in parsed_args.update.split(",") if m]
        install = [m for m in parsed_args.init.split(",") if m]
        if not upgrade and not install:
            self.parser.error("name at least one module with -u or -i")

        from odoo.modules.registry import Registry

        recorder = _Recorder()
        handler = _MigrationLog(recorder)
        logging.getLogger("odoo.modules.migration").addHandler(handler)
        registry = Registry(db_name)
        error: BaseException | None = None
        try:
            with registry.cursor() as real:
                opened = [0]
                real_execute = real.execute

                def dry_commit() -> None:
                    # what Cursor.commit does short of COMMIT: the loader's
                    # per-module commits keep the one transaction open
                    real.flush()
                    real.commit_count += 1
                    real.clear()
                    real.prerollback.clear()
                    real.postrollback.clear()
                    real.postcommit.clear()

                def recording_execute(
                    query: typing.Any, *args: typing.Any, **kw: typing.Any
                ) -> None:
                    recorder.record(query)
                    return real_execute(query, *args, **kw)

                def open_dry(
                    self: typing.Any, readonly: bool = False, **kwargs: typing.Any
                ) -> BaseCursor:
                    # the loader insists on a real Cursor and commits per
                    # module; every opener gets the one real cursor with its
                    # COMMIT, ROLLBACK and close disarmed, so the whole run is
                    # a single transaction the command rolls back at the end
                    opened[0] += 1
                    return real

                real.commit = dry_commit  # type: ignore[method-assign]
                real.rollback = lambda: None  # type: ignore[method-assign]
                real.close = lambda: None  # type: ignore[method-assign]
                real.execute = recording_execute  # type: ignore[method-assign]
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(Registry, "cursor", open_dry))
                    for name, value in (
                        ("setup_signaling", lambda self: None),
                        ("check_signaling", lambda self: self),
                        ("signal_changes", lambda self: None),
                    ):
                        stack.enter_context(patch.object(Registry, name, value))
                    try:
                        Registry.new(
                            db_name,
                            update_module=True,
                            upgrade_modules=upgrade,
                            install_modules=install,
                            run_tests=False,
                        )
                    except Exception as exc:
                        error = exc
                    finally:
                        for name in ("commit", "rollback", "close", "execute"):
                            vars(real).pop(name, None)
                        real.rollback()
        finally:
            logging.getLogger("odoo.modules.migration").removeHandler(handler)
            Registry.remove(db_name)

        self._report(recorder, error, show_all=parsed_args.show_all)
        if error is not None:
            _logger.error("the upgrade would fail: %s", error, exc_info=error)
            sys.exit(1)

    @staticmethod
    def _report(
        recorder: _Recorder, error: BaseException | None, *, show_all: bool
    ) -> None:
        out = sys.stdout
        print(f"migrations that would run: {len(recorder.migrations)}", file=out)
        for module, version, script in recorder.migrations:
            print(f"  {module} {version} {script}", file=out)
        print(f"DDL statements that would run: {len(recorder.ddl)}", file=out)
        if show_all:
            for statement in recorder.ddl:
                print(f"  {statement}", file=out)
        else:
            shapes = Counter(_shape(statement) for statement in recorder.ddl)
            for shape, count in sorted(shapes.items()):
                print(f"  {count:5d}  {shape}", file=out)
        print("rows the catalog models would change:", file=out)
        for key, count in sorted(recorder.meta.items()):
            print(f"  {count:5d}  {key}", file=out)
        if error is not None:
            print(f"STOPPED: {type(error).__name__}: {error}", file=out)
        _debug.lifecycle(
            "cli.schema_diff.done",
            ddl=len(recorder.ddl),
            migrations=len(recorder.migrations),
            failed=error is not None,
        )


def _shape(statement: str) -> str:
    # literals and comments folded, identifiers kept: the reader wants the
    # table and the column, not the help text
    shape = re.sub(r"'[^']*'", "'…'", statement)
    shape = re.sub(r"; COMMENT ON [^;]*", "", shape)
    shape = re.sub(r"\bIS %s\b", "IS …", shape)
    return shape[:200]
