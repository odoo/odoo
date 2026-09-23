import code
import importlib.util
import logging
import os
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

import odoo
from odoo import api
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import current_worker_thread
from odoo.modules.registry import Registry
from odoo.service import server
from odoo.tools import config

from . import Command, get_single_database
from . import server as cli_server
from .command import PROG_NAME

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


"""
    Shell exit behaviors
    ====================

    Legend:
        stop = The REPL main loop stop.
        raise = Exception raised.
        loop = Stay in REPL.

   Shell  | ^D    | exit() | quit() | sys.exit() | raise SystemExit()
----------------------------------------------------------------------
 python   | stop  | raise  | raise  | raise      | raise
 ipython  | stop  | stop   | stop   | loop       | loop
 ptpython | stop  | raise  | raise  | raise      | raise
 bpython  | stop  | stop   | stop   | stop       | stop

"""


def raise_keyboard_interrupt(*a: Any) -> NoReturn:
    raise KeyboardInterrupt


class Console(code.InteractiveConsole):
    def __init__(
        self, local_vars: dict[str, Any] | None = None, filename: str = "<console>"
    ) -> None:
        super().__init__(locals=local_vars, filename=filename)
        try:
            import readline
            import rlcompleter
        except ImportError:
            _debug.logic("cli.shell.readline_unavailable")
            print("readline or rlcompleter not available, autocomplete disabled.")
        else:
            readline.set_completer(rlcompleter.Completer(local_vars).complete)
            readline.parse_and_bind("tab: complete")
            _debug.logic(
                "cli.shell.completer_bound", names=len(local_vars) if local_vars else 0
            )


class Shell(Command):
    description = "Start odoo in an interactive shell"
    supported_shells = ("ipython", "ptpython", "bpython", "python")
    _REPL_MODULES = {"ipython": "IPython", "ptpython": "ptpython", "bpython": "bpython"}

    def __init__(self) -> None:
        super().__init__()
        self._shell_file: str = ""
        self._shell_interface: str | None = None
        self.parser.add_argument(
            "--shell-file",
            dest="shell_file",
            default="",
            help="Specify a python script to be run after the start of the shell. "
            "Overrides the env variable PYTHONSTARTUP.",
        )
        self.parser.add_argument(
            "--shell-interface",
            dest="shell_interface",
            choices=self.supported_shells,
            help="Specify a preferred REPL to use in shell mode. "
            f"Supported REPLs are: {self.supported_shells}",
        )

    @classmethod
    def _is_repl_installed(cls, shell: str) -> bool:
        module = cls._REPL_MODULES.get(shell)
        if module is None:
            return True
        try:
            return importlib.util.find_spec(module) is not None
        except ImportError, ValueError:
            return False

    def _start_server(self, args: list[str]) -> None:
        parsed_args, remaining = self.parser.parse_known_args(args)
        self._shell_file = parsed_args.shell_file
        self._shell_interface = parsed_args.shell_interface

        with _debug.perf("cli.config.parse", command="shell", args=len(remaining)):
            config.parse_config(remaining, setup_logging=True)
        cli_server.report_configuration()
        with _debug.perf("cli.shell.server_start"):
            server.start(preload=[], stop=True)
        signal.signal(signal.SIGINT, raise_keyboard_interrupt)
        _debug.lifecycle(
            "cli.shell.server_ready",
            shell_file=bool(self._shell_file),
            interface=self._shell_interface,
        )

    @staticmethod
    def _is_stdin_a_tty() -> bool:
        try:
            return sys.stdin is not None and os.isatty(sys.stdin.fileno())
        except AttributeError, OSError, ValueError:
            _debug.logic("cli.shell.stdin_probe_failed")
            return False

    def _enter_console(self, local_vars: dict[str, Any]) -> None:
        if not self._is_stdin_a_tty():
            _debug.logic("cli.shell.mode", mode="piped_stdin")
            local_vars["__name__"] = "__main__"
            with _debug.perf("cli.shell.script", source="stdin"):
                exec(sys.stdin.read(), local_vars)  # noqa: S102  piped-in script IS what `odoo shell` runs
            return None

        if "env" not in local_vars:
            print(f"No environment set, use `{PROG_NAME} shell -d dbname` to get one.")
        for i in sorted(local_vars):
            print(f"{i}: {local_vars[i]}")

        pythonstartup = self._shell_file or os.environ.get("PYTHONSTARTUP")

        preferred_interface = self._shell_interface
        if preferred_interface:
            shells_to_try = list(dict.fromkeys([preferred_interface, "python"]))
        else:
            shells_to_try = list(self.supported_shells)

        _debug.logic(
            "cli.shell.mode",
            mode="interactive",
            preferred=preferred_interface,
            candidates=len(shells_to_try),
            startup_file=bool(pythonstartup),
        )
        for shell in shells_to_try:
            if not self._is_repl_installed(shell):
                _debug.logic(
                    "cli.shell.repl_skipped",
                    shell=shell,
                    reason="not_installed",
                    preferred=shell == preferred_interface,
                )
                if shell == preferred_interface:
                    _logger.warning(
                        "Requested shell %r is not installed; falling back.",
                        preferred_interface,
                    )
                continue
            try:
                shell_func = self._get_repl_launchers()[shell]
                _debug.lifecycle("cli.shell.repl_started", shell=shell)
                result = shell_func(local_vars, pythonstartup)
                _debug.lifecycle("cli.shell.repl_exited", shell=shell)
                return result
            except Exception as e:
                _debug.logic(
                    "cli.shell.repl_skipped",
                    shell=shell,
                    reason="start_failed",
                    error=type(e).__name__,
                )
                _logger.warning("Could not start '%s' shell.", shell)
                _logger.debug("Shell error:", exc_info=True)
        _debug.logic("cli.shell.no_repl", candidates=len(shells_to_try))
        return None

    def _get_repl_launchers(
        self,
    ) -> dict[str, Callable[[dict[str, Any], str | None], None]]:
        return {
            "ipython": self.ipython,
            "ptpython": self.ptpython,
            "bpython": self.bpython,
            "python": self.python,
        }

    def ipython(
        self, local_vars: dict[str, Any], pythonstartup: str | None = None
    ) -> None:
        from IPython import start_ipython

        argv = ["--TerminalIPythonApp.display_banner=False"] + (
            [f"--TerminalIPythonApp.exec_files={pythonstartup}"]
            if pythonstartup
            else []
        )
        start_ipython(argv=argv, user_ns=local_vars)

    def ptpython(
        self, local_vars: dict[str, Any], pythonstartup: str | None = None
    ) -> None:
        from ptpython.repl import embed

        embed(
            {},
            local_vars,
            startup_paths=[pythonstartup] if pythonstartup else None,
        )

    def bpython(
        self, local_vars: dict[str, Any], pythonstartup: str | None = None
    ) -> None:
        from bpython import embed

        embed(
            local_vars,
            args=["-q", "-i", pythonstartup] if pythonstartup else None,
        )

    def python(
        self, local_vars: dict[str, Any], pythonstartup: str | None = None
    ) -> None:
        console = Console(local_vars)
        if pythonstartup:
            with _debug.perf("cli.shell.script", source=pythonstartup):
                console.runsource(
                    Path(pythonstartup).read_text(encoding="utf-8"),
                    filename=pythonstartup,
                    symbol="exec",
                )
        with _debug.perf("cli.shell.interact", repl="python"):
            console.interact(banner="")

    def _start_shell(self, dbname: str | None) -> None:
        local_vars: dict[str, Any] = {
            "odoo": odoo,
        }
        if dbname:
            current_worker_thread().dbname = dbname
            with _debug.perf("cli.registry", db=dbname, new_registry=False):
                registry = Registry(dbname)
            with registry.cursor() as cr:
                uid = api.SUPERUSER_ID
                with _debug.perf("cli.shell.context", cr=cr, db=dbname, uid=uid):
                    ctx = api.Environment(cr, uid, {})["res.users"].context_get()
                env = api.Environment(cr, uid, ctx)
                env.transaction.default_env = env
                local_vars["env"] = env
                local_vars["self"] = env.user
                cr.rollback()
                _debug.lifecycle(
                    "cli.shell.env_ready", db=dbname, uid=uid, lang=ctx.get("lang")
                )
                with _debug.perf("cli.shell.session", cr=cr, db=dbname):
                    self._enter_console(local_vars)
                cr.rollback()
                _debug.lifecycle("cli.shell.session_rolled_back", db=dbname)
        else:
            _debug.lifecycle("cli.shell.env_ready", db=None)
            self._enter_console(local_vars)

    def run(self, args: list[str]) -> None:
        self._start_server(args)
        dbname = get_single_database(config["db_name"], allow_none=True)
        _debug.lifecycle("cli.shell", db=dbname)
        self._start_shell(dbname)
        _debug.lifecycle("cli.shell.done", db=dbname)
