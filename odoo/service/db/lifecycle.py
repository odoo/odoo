import logging
import os
import shutil
import time
from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import psycopg
from psycopg import sql as psycopg_sql

import odoo.api
import odoo.db
import odoo.modules.db
import odoo.modules.neutralize
import odoo.modules.registry
import odoo.tools
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.constants import CRON_TRIGGER_CHANNEL, JOB_QUEUE_CHANNEL

from ._checks import check_db_management_enabled, check_db_name
from .listing import check_db_exposed, invalidate_catalog_caches

if TYPE_CHECKING:
    from odoo.db import BaseCursor
else:
    BaseCursor = Any

_logger = logging.getLogger("odoo.service.db")
_debug = DebugLog(__name__)


class DatabaseExists(Warning):
    pass


def get_database_identifier(cr: BaseCursor, name: str) -> SQL:
    name = psycopg_sql.Identifier(name).as_string(cr.connection)
    return SQL(name.replace("%", "%%"))


def _terminate_backends(cr: BaseCursor, db_name: str) -> None:
    try:
        with _debug.perf("database.backends_terminated", db=db_name) as span:
            cr.execute(
                """SELECT pg_terminate_backend(pid)
                          FROM pg_stat_activity
                          WHERE datname = %s AND
                                pid != pg_backend_pid()""",
                (db_name,),
            )
            span.set(backends=getattr(cr, "rowcount", None))
    except Exception:
        _logger.debug("pg_terminate_backend failed for %r", db_name, exc_info=True)
        _debug.logic("database.backends_terminate_failed", db=db_name)


def _create_faketime_now_function(db_name: str) -> None:
    if not os.getenv("ODOO_FAKETIME_TEST_MODE"):
        return
    if not odoo.tools.config["test_enable"]:
        _logger.warning(
            "ODOO_FAKETIME_TEST_MODE is set but --test-enable is not active. "
            "Refusing to install faketime now() into %r.",
            db_name,
        )
        _debug.logic("database.faketime_refused", db=db_name, reason="no_test_enable")
        return
    configured_dbs = odoo.tools.config["db_name"] or ()
    if db_name not in configured_dbs:
        _debug.logic("database.faketime_refused", db=db_name, reason="not_configured")
        return
    try:
        db = odoo.db.db_connect(db_name)
        with db.cursor() as cursor:
            cursor.execute("SELECT (pg_catalog.now() AT TIME ZONE 'UTC');")
            server_now_row = cursor.fetchone()
            assert server_now_row is not None, "SELECT now() returned no row"
            server_now = server_now_row[0]
            time_offset = (datetime.now() - server_now).total_seconds()

            cursor.execute(
                """
                CREATE OR REPLACE FUNCTION public.now()
                    RETURNS timestamp with time zone AS $$
                        SELECT pg_catalog.now() +  %s * interval '1 second';
                    $$ LANGUAGE sql;
            """,
                (int(time_offset),),
            )
            cursor.execute("SELECT (now() AT TIME ZONE 'UTC');")
            new_now_row = cursor.fetchone()
            new_now = new_now_row[0] if new_now_row else None
            _logger.info("Faketime mode, new cursor now is %s", new_now)
            cursor.commit()
            _debug.lifecycle(
                "database.faketime_installed", db=db_name, offset_s=int(time_offset)
            )
    except psycopg.Error as e:
        _logger.warning("Unable to set faketime NOW(): %s", e)
        _debug.logic("database.faketime_failed", db=db_name, error=type(e).__name__)


def _warn_on_non_c_template(cr, template: str) -> None:
    cr.execute("SELECT datcollate FROM pg_database WHERE datname = %s", (template,))
    row = cr.fetchone()
    if row is not None and row[0] != "C":
        _debug.logic("database.template_non_c", template=template, collate=row[0])
        _logger.warning(
            "db_template %r has LC_COLLATE=%r, not 'C'; databases created from "
            "it inherit that collation, so SQL ORDER BY and in-memory "
            "recordset.sorted() will disagree on text. Rebuild the template "
            "from template0 with LC_COLLATE 'C' to restore the invariant.",
            template,
            row[0],
        )


def _create_empty_database(
    name: str,
    template: str | None = None,
    force_unaccent: bool = False,
    setup_if_exists: bool = True,
) -> None:
    db = odoo.db.db_connect("postgres")
    with closing(db.cursor()) as cr:
        chosen_template = template or odoo.tools.config["db_template"]
        check_db_name(chosen_template)
        cr.rollback()
        cr.connection.autocommit = True

        if chosen_template == "template0":
            create_sql = SQL(
                "CREATE DATABASE %s ENCODING 'unicode' LC_COLLATE 'C' TEMPLATE %s",
                get_database_identifier(cr, name),
                get_database_identifier(cr, chosen_template),
            )
        else:
            _warn_on_non_c_template(cr, chosen_template)
            create_sql = SQL(
                "CREATE DATABASE %s ENCODING 'unicode' TEMPLATE %s",
                get_database_identifier(cr, name),
                get_database_identifier(cr, chosen_template),
            )
        already_exists = False

        def _create() -> None:
            nonlocal already_exists
            try:
                cr.execute(  # noqa: E8501  parameterised SQL(), built above
                    create_sql, log_exceptions=False
                )
            except psycopg.errors.DuplicateDatabase, psycopg.errors.UniqueViolation:
                already_exists = True

        with _debug.perf("database.create_ddl", db=name, template=chosen_template):
            _retry_on_object_in_use(
                f"CREATE DB: {name} (template {chosen_template})", _create
            )

    _debug.lifecycle(
        "database.created",
        db=name,
        template=chosen_template,
        already_exists=already_exists,
        setup_if_exists=setup_if_exists,
        unaccent=bool(force_unaccent or odoo.tools.config.get("unaccent")),
    )
    if already_exists and not setup_if_exists:
        raise DatabaseExists(f"database {name!r} already exists!")

    with odoo.db.db_connect(name).cursor() as cr:
        _create_extensions(cr, name, force_unaccent or odoo.tools.config["unaccent"])
        _open_public_schema(cr, name)
    _create_faketime_now_function(name)

    invalidate_catalog_caches()

    if already_exists:
        raise DatabaseExists(f"database {name!r} already exists!")


def _create_extensions(cr: BaseCursor, name: str, unaccent: bool) -> None:
    try:
        with cr.savepoint(flush=False):
            cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            if unaccent:
                cr.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
                unaccent_status = odoo.db.get_unaccent_status(cr)
                _debug.logic(
                    "database.unaccent_status",
                    db=name,
                    status=getattr(unaccent_status, "name", unaccent_status),
                )
                if unaccent_status != odoo.db.FunctionStatus.INDEXABLE:
                    cr.execute(
                        "ALTER FUNCTION unaccent(text) IMMUTABLE",
                        log_exceptions=False,
                    )
        _debug.pipeline("database.extensions_created", db=name, unaccent=unaccent)
    except psycopg.Error as e:
        _debug.logic("database.extensions_failed", db=name, error=type(e).__name__)
        _logger.error(
            "Unable to create PostgreSQL extensions in %r: %s. "
            "Check that postgresql-contrib is installed and the DB role has "
            "CREATE EXTENSION privileges; without pg_trgm/unaccent, search "
            "queries on this database will fall back to slower paths.",
            name,
            e,
        )


def _open_public_schema(cr: BaseCursor, name: str) -> None:
    try:
        with cr.savepoint(flush=False):
            cr.execute("GRANT CREATE ON SCHEMA PUBLIC TO PUBLIC")
    except psycopg.Error as e:
        _logger.warning("Unable to make public schema public-accessible: %s", e)
        _debug.logic("database.public_grant_failed", db=name, error=type(e).__name__)


def _announce_database(db_name: str) -> None:
    # A listener sweeping from the catalogue admits a name it has never
    # listed only on a notify for it (`CronSchedule`); nothing in a fresh
    # database sends one until a job triggers, so its scheduled crons would
    # wait for the next periodic sweep.
    try:
        with closing(odoo.db.db_connect("postgres").cursor()) as cr:
            cr.connection.autocommit = True
            for channel in (CRON_TRIGGER_CHANNEL, JOB_QUEUE_CHANNEL):
                cr.execute("SELECT pg_notify(%s, %s)", (channel, db_name))
    except Exception:
        _logger.debug("Could not announce database %r to the listeners", db_name)
        _debug.logic("database.announce_failed", db=db_name)
        return
    _debug.lifecycle("database.announced", db=db_name)


def _rollback_new_database(db_name: str, what: str) -> None:
    _logger.info("%s: rolling back database %r after failure", what, db_name)
    _debug.lifecycle("database.rollback", db=db_name, what=what)
    try:
        dropped = drop_database(db_name)
        _debug.lifecycle("database.rolled_back", db=db_name, what=what, dropped=dropped)
    except Exception:
        _logger.exception(
            "%s: could not remove database %r after failure; manual cleanup required",
            what,
            db_name,
        )
        _debug.logic("database.rollback_failed", db=db_name, what=what)


def _check_filestore_dest_free(dest: str, problem: str) -> None:
    if Path(dest).exists():
        _debug.logic("database.filestore_dest_taken", dest=dest)
        raise RuntimeError(
            f"{problem}: destination filestore {dest!r} already exists.  "
            f"Move or delete the stale directory before retrying."
        )


@check_db_management_enabled
def exp_create_database(
    db_name: str,
    demo: bool,
    lang: str,
    user_password: str = "admin",
    login: str = "admin",
    country_code: str | None = None,
    phone: str | None = None,
) -> Literal[True]:
    check_db_name(db_name)
    _check_filestore_dest_free(
        odoo.tools.config.filestore(db_name), f"Cannot create {db_name!r}"
    )
    _logger.info("Create database `%s`.", db_name)
    _create_empty_database(db_name, setup_if_exists=False)
    try:
        with _debug.perf(
            "database.initialized",
            db=db_name,
            demo=demo,
            lang=lang,
            country=country_code,
        ):
            odoo.modules.db.initialize_db(
                db_name, demo, lang, user_password, login, country_code, phone
            )
    except Exception:
        _rollback_new_database(db_name, "CREATE DB")
        raise
    _announce_database(db_name)
    return True


@check_db_management_enabled
def exp_duplicate_database(
    db_original_name: str,
    db_name: str,
    neutralize_database: bool = False,
) -> Literal[True]:
    check_db_exposed(db_original_name)
    return duplicate_database(db_original_name, db_name, neutralize_database)


def duplicate_database(
    db_original_name: str,
    db_name: str,
    neutralize_database: bool = False,
) -> Literal[True]:
    check_db_name(db_name)

    to_fs = odoo.tools.config.filestore(db_name)
    _check_filestore_dest_free(to_fs, f"Cannot duplicate to {db_name!r}")

    _logger.info("Duplicate database `%s` to `%s`.", db_original_name, db_name)
    odoo.db.close_db(db_original_name)
    db = odoo.db.db_connect("postgres")
    with closing(db.cursor()) as cr:
        cr.connection.autocommit = True

        def _create_from_template() -> None:
            try:
                cr.execute(
                    SQL(
                        "CREATE DATABASE %s ENCODING 'unicode' TEMPLATE %s",
                        get_database_identifier(cr, db_name),
                        get_database_identifier(cr, db_original_name),
                    )
                )
            except (
                psycopg.errors.DuplicateDatabase,
                psycopg.errors.UniqueViolation,
            ) as exc:
                raise DatabaseExists(f"database {db_name!r} already exists!") from exc

        with _debug.perf("database.duplicate_ddl", source=db_original_name, db=db_name):
            _retry_terminate_then_ddl(
                cr,
                db_original_name,
                f"DUPLICATE DB: {db_original_name} -> {db_name}",
                _create_from_template,
            )

    try:
        with _debug.perf("database.duplicate.registry_loaded", db=db_name):
            registry = odoo.modules.registry.Registry.new(db_name, run_tests=False)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.api.SUPERUSER_ID, {})
            env["ir.config_parameter"].init(force=True)
            if neutralize_database:
                with _debug.perf("database.duplicate.neutralized", cr=cr, db=db_name):
                    odoo.modules.neutralize.neutralize_database(cr)

        from_fs = odoo.tools.config.filestore(db_original_name)
        if Path(from_fs).exists():
            if Path(to_fs).exists():
                raise RuntimeError(
                    f"Filestore {to_fs!r} appeared between pre-flight and copy (race)."
                )
            with _debug.perf("database.filestore_copied", db=db_name):
                shutil.copytree(from_fs, to_fs)
    except Exception:
        _rollback_new_database(db_name, "DUPLICATE DB")
        raise
    _debug.lifecycle(
        "database.duplicated",
        source=db_original_name,
        db=db_name,
        neutralized=neutralize_database,
        filestore=Path(to_fs).exists(),
    )
    invalidate_catalog_caches()
    _announce_database(db_name)
    return True


_DROP_DATABASE_MAX_RETRIES = 5


_DROP_DATABASE_BACKOFF_BASE = 0.2


def _retry_on_object_in_use(
    op_label: str,
    run: Callable[[], None],
    *,
    before_attempt: Callable[[], None] | None = None,
) -> None:
    last_error: psycopg.errors.ObjectInUse | None = None
    for attempt in range(1, _DROP_DATABASE_MAX_RETRIES + 1):
        if before_attempt is not None:
            before_attempt()
        try:
            run()
        except psycopg.errors.ObjectInUse as e:
            last_error = e
            _logger.info(
                "%s attempt %d/%d, still in use: %s",
                op_label,
                attempt,
                _DROP_DATABASE_MAX_RETRIES,
                e,
            )
            _debug.logic(
                "database.ddl.object_in_use",
                operation=op_label,
                attempt=attempt,
                max_attempts=_DROP_DATABASE_MAX_RETRIES,
            )
            if attempt < _DROP_DATABASE_MAX_RETRIES:
                time.sleep(_DROP_DATABASE_BACKOFF_BASE * (2 ** (attempt - 1)))
        else:
            if _debug.logic.enabled and attempt > 1:
                _debug.logic(
                    "database.ddl.succeeded_after_retry",
                    operation=op_label,
                    attempt=attempt,
                )
            return
    _debug.logic(
        "database.ddl.retries_exhausted",
        operation=op_label,
        attempts=_DROP_DATABASE_MAX_RETRIES,
    )
    raise RuntimeError(
        f"{op_label}: still in use after {_DROP_DATABASE_MAX_RETRIES} "
        f"attempts: {last_error}"
    ) from last_error


def _retry_terminate_then_ddl(
    cr: BaseCursor,
    terminate_target: str,
    op_label: str,
    run: Callable[[], None],
) -> None:
    _retry_on_object_in_use(
        op_label, run, before_attempt=lambda: _terminate_backends(cr, terminate_target)
    )


def _database_exists(db_name: str) -> bool:
    try:
        with closing(odoo.db.db_connect("postgres").cursor()) as cr:
            cr.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            return cr.fetchone() is not None
    except Exception:
        # Unknown is treated as present: the DROP below reports the truth.
        _logger.debug("DROP DB %r: existence probe failed", db_name, exc_info=True)
        _debug.logic("database.drop.probe_failed", db=db_name)
        return True


def drop_database(db_name: str) -> bool:
    if not _database_exists(db_name):
        _debug.logic("database.drop.absent", db=db_name)
        return False
    odoo.modules.registry.Registry.clear_database_state(db_name)
    odoo.db.close_db(db_name)

    db = odoo.db.db_connect("postgres")
    with closing(db.cursor()) as cr:
        cr.connection.autocommit = True

        def _drop() -> None:
            try:
                cr.execute(
                    SQL("DROP DATABASE %s", get_database_identifier(cr, db_name))
                )
            except psycopg.errors.ObjectInUse:
                raise
            except Exception as e:
                _logger.info("DROP DB: %s failed:\n%s", db_name, e)
                raise RuntimeError(f"Couldn't drop database {db_name}: {e}") from e
            _logger.info("DROP DB: %s", db_name)

        with _debug.perf("database.drop_ddl", db=db_name):
            _retry_terminate_then_ddl(cr, db_name, f"DROP DB: {db_name}", _drop)

    odoo.db.close_db(db_name)

    fs = odoo.tools.config.filestore(db_name)
    _debug.lifecycle("database.dropped", db=db_name, filestore=Path(fs).exists())
    if Path(fs).exists():
        with _debug.perf("database.filestore_removed", db=db_name):
            shutil.rmtree(fs)
    invalidate_catalog_caches()
    return True


@check_db_management_enabled
def exp_drop(db_name: str) -> bool:
    check_db_exposed(db_name)
    return drop_database(db_name)


@check_db_management_enabled
def exp_rename(old_name: str, new_name: str) -> Literal[True]:
    check_db_exposed(old_name)
    return rename_database(old_name, new_name)


def rename_database(old_name: str, new_name: str) -> Literal[True]:
    check_db_name(new_name)

    old_fs = odoo.tools.config.filestore(old_name)
    new_fs = odoo.tools.config.filestore(new_name)
    _check_filestore_dest_free(
        new_fs, f"Cannot rename database {old_name!r} to {new_name!r}"
    )

    odoo.modules.registry.Registry.clear_database_state(old_name)
    odoo.db.close_db(old_name)

    db = odoo.db.db_connect("postgres")
    with closing(db.cursor()) as cr:
        cr.connection.autocommit = True

        def _rename() -> None:
            try:
                cr.execute(
                    SQL(
                        "ALTER DATABASE %s RENAME TO %s",
                        get_database_identifier(cr, old_name),
                        get_database_identifier(cr, new_name),
                    )
                )
            except (
                psycopg.errors.DuplicateDatabase,
                psycopg.errors.UniqueViolation,
            ) as exc:
                raise DatabaseExists(f"database {new_name!r} already exists!") from exc
            except psycopg.errors.ObjectInUse:
                raise
            except Exception as e:
                _logger.info("RENAME DB: %s -> %s failed:\n%s", old_name, new_name, e)
                raise RuntimeError(
                    f"Couldn't rename database {old_name!r} to {new_name!r}: {e}"
                ) from e
            _logger.info("RENAME DB: %s -> %s", old_name, new_name)

        with _debug.perf("database.rename_ddl", source=old_name, db=new_name):
            _retry_terminate_then_ddl(
                cr, old_name, f"RENAME DB: {old_name} -> {new_name}", _rename
            )

        if Path(old_fs).exists():
            if Path(new_fs).exists():
                _rollback_db_rename(cr, old_name, new_name)
                raise RuntimeError(
                    f"Filestore {new_fs!r} appeared between pre-flight and "
                    f"move (race).  Database rename rolled back."
                )
            try:
                with _debug.perf("database.rename.filestore_moved", db=new_name):
                    shutil.move(old_fs, new_fs)
            except Exception as fs_err:
                _logger.error(
                    "RENAME DB: filestore move %r -> %r failed (%s); "
                    "rolling back DB rename",
                    old_fs,
                    new_fs,
                    fs_err,
                )
                _debug.logic(
                    "database.rename.filestore_move_failed",
                    source=old_name,
                    db=new_name,
                    error=type(fs_err).__name__,
                )
                try:
                    _rollback_db_rename(cr, old_name, new_name)
                except Exception as revert_err:
                    raise RuntimeError(
                        f"Couldn't rename filestore {old_fs!r} -> {new_fs!r} "
                        f"({fs_err}); ALSO failed to roll back DB rename "
                        f"{new_name!r} -> {old_name!r} ({revert_err}). "
                        f"Database and filestore are out of sync — manual "
                        f"intervention required."
                    ) from fs_err
                raise RuntimeError(
                    f"Couldn't rename filestore {old_fs!r} -> {new_fs!r}: "
                    f"{fs_err}. Database rename rolled back."
                ) from fs_err
    _debug.lifecycle(
        "database.renamed",
        source=old_name,
        db=new_name,
        filestore=Path(new_fs).exists(),
    )
    invalidate_catalog_caches()
    _announce_database(new_name)
    return True


def _rollback_db_rename(cr: BaseCursor, old_name: str, new_name: str) -> None:
    _debug.lifecycle("database.rename.rolled_back", source=old_name, db=new_name)

    def _rename_back() -> None:
        cr.execute(
            SQL(
                "ALTER DATABASE %s RENAME TO %s",
                get_database_identifier(cr, new_name),
                get_database_identifier(cr, old_name),
            )
        )

    # A backend can connect to the new name between the rename and this
    # rollback (a catalog sweep, another cluster member, a curious psql).
    # The forward rename already terminates and retries on ObjectInUse;
    # giving up here instead escalates a recoverable race to "database and
    # filestore are out of sync — manual intervention required".
    _retry_terminate_then_ddl(
        cr, new_name, f"ROLLBACK RENAME DB: {new_name} -> {old_name}", _rename_back
    )
