import atexit
import contextlib
import logging
import os
import sys
from pathlib import Path

from psycopg.errors import InsufficientPrivilege

import odoo
import odoo.release  # noqa: F401  binds the submodule so `odoo.release.version` resolves below
from odoo.libs.debug_log import DebugLog
from odoo.libs.memory_watch import start_from_environ as start_memory_watch
from odoo.service import db, server
from odoo.tools import config

from . import Command
from .command import check_db_not_maintenance

_logger = logging.getLogger("odoo")
_debug = DebugLog(__name__)


def warn_running_as_root() -> None:
    if os.name == "posix" and os.getuid() == 0:
        _debug.logic("cli.server.running_as_root")
        sys.stderr.write("Running as user 'root' is a security risk.\n")


def check_db_user_not_postgres() -> None:
    if (config["db_user"] or os.environ.get("PGUSER")) == "postgres":
        _debug.logic("cli.server.refused", reason="postgres_db_user")
        sys.stderr.write(
            "Using the database user 'postgres' is a security risk, aborting.\n"
        )
        sys.exit(1)


def report_configuration() -> None:
    import odoo.addons

    _logger.info("Odoo version %s", odoo.release.version)
    if Path(config["config"]).is_file():
        _logger.info("Using configuration file at %s", config["config"])
    _logger.info("addons paths: %s", odoo.addons.__path__)
    if config.get("upgrade_path"):
        _logger.info("upgrade path: %s", config["upgrade_path"])
    if config.get("pre_upgrade_scripts"):
        _logger.info("extra upgrade scripts: %s", config["pre_upgrade_scripts"])
    host = config["db_host"] or os.environ.get("PGHOST", "default")
    port = config["db_port"] or os.environ.get("PGPORT", "default")
    user = config["db_user"] or os.environ.get("PGUSER", "default")
    _logger.info("database: %s@%s:%s", user, host, port)
    replica_host = config["db_replica_host"]
    replica_port = config["db_replica_port"]
    _debug.pipeline(
        "cli.server.configured",
        config_file=Path(config["config"]).is_file(),
        addons_paths=len(odoo.addons.__path__),
        db_names=len(config["db_name"]),
        db_host=host,
        replica=bool(replica_host or replica_port),
        upgrade_path=bool(config.get("upgrade_path")),
        dev_mode=len(config["dev_mode"]),
    )
    if replica_host or replica_port or "replica" in config["dev_mode"]:
        _logger.info(
            "replica database: %s@%s:%s",
            user,
            replica_host or "default",
            replica_port or "default",
        )
    if sys.version_info[:2] > odoo.release.MAX_PY_VERSION:
        _debug.logic(
            "cli.server.python_unsupported",
            version=".".join(map(str, sys.version_info[:2])),
            max=".".join(map(str, odoo.release.MAX_PY_VERSION)),
        )
        _logger.warning(
            "Python %s is not officially supported, please use Python %s instead",
            ".".join(map(str, sys.version_info[:2])),
            ".".join(map(str, odoo.release.MAX_PY_VERSION)),
        )


def remove_pid_file(main_pid: int) -> None:
    if config["pidfile"] and main_pid == os.getpid():
        with contextlib.suppress(OSError):
            Path(config["pidfile"]).unlink()
            _debug.lifecycle(
                "cli.server.pid_removed", pid=main_pid, path=config["pidfile"]
            )
        return
    _debug.logic(
        "cli.server.pid_remove_skipped",
        reason="no_pidfile" if not config["pidfile"] else "child_process",
        pid=os.getpid(),
    )


def write_pid_file() -> None:
    # Reload candidates are children of the persistent supervisor. They must
    # neither replace its PID file nor register cleanup that removes it.
    if int(os.environ.get("ODOO_RELOAD_SUPERVISOR_PID", "0")):
        _debug.logic("cli.server.pid_skipped", reason="reload_candidate")
        return
    if not odoo.evented and config["pidfile"]:
        pid = os.getpid()
        Path(config["pidfile"]).write_text(str(pid), encoding="utf-8")
        atexit.register(remove_pid_file, pid)
        _debug.lifecycle("cli.server.pid_written", pid=pid, path=config["pidfile"])
        return
    _debug.logic(
        "cli.server.pid_skipped",
        reason="evented" if odoo.evented else "no_pidfile",
    )


def create_configured_databases() -> None:
    # The evented child is spawned by a master that already ran this, and it
    # never loads a registry, so it has no database to create or extend.
    if odoo.evented:
        _debug.logic("cli.server.database_probe_skipped", reason="evented")
        return
    for db_name in config["db_name"]:
        try:
            with _debug.perf("cli.server.create_empty_database", db=db_name):
                db._create_empty_database(db_name)
            config["init"]["base"] = True
            _debug.lifecycle("cli.server.database_created", db=db_name, init_base=True)
        except InsufficientPrivilege as err:
            _debug.logic(
                "cli.server.database_probe", db=db_name, outcome="no_privilege"
            )
            _logger.info(
                "Could not determine if database %s exists, skipping auto-creation: %s",
                db_name,
                err,
            )
        except db.DatabaseExists:
            _debug.logic("cli.server.database_probe", db=db_name, outcome="exists")
            pass
        except Exception as err:
            _debug.logic(
                "cli.server.database_probe",
                db=db_name,
                outcome="create_failed",
                error=type(err).__name__,
            )
            sys.exit(f"Could not create database {db_name!r}. ({err})")


def run_server(args: list[str]) -> None:
    warn_running_as_root()
    with _debug.perf("cli.config.parse", command="server", args=len(args)):
        config.parse_config(args, setup_logging=True)
    check_db_user_not_postgres()
    report_configuration()
    start_memory_watch()

    for db_name in config["db_name"]:
        check_db_not_maintenance(
            db_name,
            error_handler=lambda msg: sys.exit(
                f"{msg} Choose another with -d/--database, or db_name in the "
                "config file."
            ),
        )
    _debug.pipeline("cli.server.databases_checked", count=len(config["db_name"]))

    with _debug.perf("cli.server.database_probes", databases=len(config["db_name"])):
        create_configured_databases()

    stop = config["stop_after_init"]

    write_pid_file()
    _debug.lifecycle(
        "cli.server.start",
        pid=os.getpid(),
        databases=len(config["db_name"]),
        stop_after_init=stop,
        workers=config["workers"],
        evented=odoo.evented,
        test_enable=config["test_enable"],
        init=len(config["init"]),
        update=len(config["update"]),
    )
    with _debug.perf("cli.server.run", stop_after_init=stop):
        rc = server.start(preload=config["db_name"], stop=stop)
    _debug.lifecycle("cli.server.exit", rc=rc)
    sys.exit(rc)


class Server(Command):
    description = "Start the odoo server (default command)"

    def run(self, args: list[str]) -> None:
        config.parser.prog = self.prog
        _debug.pipeline("cli.server.dispatch", args=len(args))
        run_server(args)
