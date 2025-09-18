import code
import logging
import os
import signal
import sys
import threading
from pathlib import Path

import odoo  # to expose in the shell
from odoo import api
from odoo.modules.registry import Registry
from odoo.service import server
from odoo.tools import config

from . import Command, get_single_database
from . import server as cli_server

_logger = logging.getLogger(__name__)


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


def raise_keyboard_interrupt(*a):
    raise KeyboardInterrupt


class Console(code.InteractiveConsole):
    def __init__(self, local_vars=None, filename="<console>"):
        super().__init__(locals=local_vars, filename=filename)
        try:
            import readline
            import rlcompleter
        except ImportError:
            print("readline or rlcompleter not available, autocomplete disabled.")
        else:
            readline.set_completer(rlcompleter.Completer(local_vars).complete)
            readline.parse_and_bind("tab: complete")


class Shell(Command):
    """Start odoo in an interactive shell"""

    supported_shells = ["ipython", "ptpython", "bpython", "python"]

    def init(self, args):
        parser = self.parser
        parser.add_argument(
            "--shell-file",
            dest="shell_file",
            default="",
            help="Specify a python script to be run after the start of the shell. "
            "Overrides the env variable PYTHONSTARTUP.",
        )
        parser.add_argument(
            "--shell-interface",
            dest="shell_interface",
            help="Specify a preferred REPL to use in shell mode. "
            "Supported REPLs are: [ipython|ptpython|bpython|python]",
        )
        # parse_known_args: shell-specific args go to parsed_args,
        # everything else is forwarded to config.parse_config for server startup
        parsed_args, remaining = parser.parse_known_args(args)
        self._shell_file = parsed_args.shell_file
        self._shell_interface = parsed_args.shell_interface

        config.parse_config(remaining, setup_logging=True)
        cli_server.report_configuration()
        server.start(preload=[], stop=True)
        signal.signal(signal.SIGINT, raise_keyboard_interrupt)

    def console(self, local_vars):
        if not os.isatty(sys.stdin.fileno()):
            local_vars["__name__"] = "__main__"
            exec(sys.stdin.read(), local_vars)  # noqa: S102 — intentional REPL exec
            return None

        if "env" not in local_vars:
            print(
                f"No environment set, use `{sys.argv[0]} shell -d dbname` to get one."
            )
        for i in sorted(local_vars):
            print(f"{i}: {local_vars[i]}")

        pythonstartup = self._shell_file or os.environ.get("PYTHONSTARTUP")

        preferred_interface = self._shell_interface
        if preferred_interface:
            shells_to_try = [preferred_interface, "python"]
        else:
            shells_to_try = self.supported_shells

        for shell in shells_to_try:
            try:
                shell_func = getattr(self, shell)
                return shell_func(local_vars, pythonstartup)
            except ImportError:
                pass
            except Exception:
                _logger.warning("Could not start '%s' shell.", shell)
                _logger.debug("Shell error:", exc_info=True)
        return None

    def ipython(self, local_vars, pythonstartup=None):
        from IPython import start_ipython

        argv = ["--TerminalIPythonApp.display_banner=False"] + (
            [f"--TerminalIPythonApp.exec_files={pythonstartup}"]
            if pythonstartup
            else []
        )
        start_ipython(argv=argv, user_ns=local_vars)

    def ptpython(self, local_vars, pythonstartup=None):
        from ptpython.repl import embed

        embed(
            {},
            local_vars,
            startup_paths=[pythonstartup] if pythonstartup else False,
        )

    def bpython(self, local_vars, pythonstartup=None):
        from bpython import embed

        embed(
            local_vars,
            args=["-q", "-i", pythonstartup] if pythonstartup else None,
        )

    def python(self, local_vars, pythonstartup=None):
        console = Console(local_vars)
        if pythonstartup:
            with Path(pythonstartup).open(encoding="utf-8") as f:
                console.runsource(f.read(), filename=pythonstartup, symbol="exec")
        console.interact(banner="")

    def shell(self, dbname):
        local_vars = {
            "odoo": odoo,
        }
        if dbname:
            threading.current_thread().dbname = dbname
            registry = Registry(dbname)
            with registry.cursor() as cr:
                uid = api.SUPERUSER_ID
                ctx = api.Environment(cr, uid, {})["res.users"].context_get()
                env = api.Environment(cr, uid, ctx)
                local_vars["env"] = env
                local_vars["self"] = env.user
                # context_get() has started the transaction already. Rollback to
                # avoid logging warning "rolling back the transaction before testing"
                # from odoo.tests.shell.run_tests if the user hasn't done anything.
                cr.rollback()
                self.console(local_vars)
                cr.rollback()
        else:
            self.console(local_vars)

    def run(self, args):
        self.init(args)
        dbname = get_single_database(config["db_name"], allow_none=True)
        self.shell(dbname)
        return 0
