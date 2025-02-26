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

import code
import logging
import optparse
import os
import signal
import sys
import threading
from contextlib import closing

import odoo
from odoo.api import Environment, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.service import server
from odoo.tools import config
from . import Command, server as cli_server

_logger = logging.getLogger(__name__)

SHELLS = ['ipython', 'ptpython', 'bpython', 'python']
SEP = '--'


class Console(code.InteractiveConsole):
    def __init__(self, local_vars=None, filename="<console>"):
        code.InteractiveConsole.__init__(self, locals=local_vars, filename=filename)
        try:
            import readline
            import rlcompleter
        except ImportError:
            print('readline or rlcompleter not available, autocomplete disabled.')
        else:
            readline.set_completer(rlcompleter.Completer(local_vars).complete)
            readline.parse_and_bind("tab: complete")


class Shell(Command):
    """Start odoo in an interactive shell"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_vars = {'odoo': odoo}

        self.interactive = os.isatty(sys.stdin.fileno())
        if self.interactive:
            self.local_vars['__name__'] = '__main__'

        config.parser.prog = self.prog
        group = optparse.OptionGroup(config.parser, "Shell options")
        group.add_option(
            '--shell-file', dest='shell_file', type='string', my_default='',
            help="Specify a python script to be run after the start of the shell. "
                 "Overrides the env variable PYTHONSTARTUP."
        )
        group.add_option(
            '--shell-interface', dest='shell_interface', type='string',
            help=(
                "Specify a preferred REPL to use in shell mode."
                f" Supported REPLs are: [{'|'.join(SHELLS)}]"
            )
        )
        config.parser.add_option_group(group)

    def _execute(self):
        exec(sys.stdin.read(), self.local_vars)

    def console(self):
        if 'env' not in self.local_vars:
            print('No environment set, use `%s shell -d dbname` to get one.' % sys.argv[0])
        for i in sorted(self.local_vars):
            print('%s: %s' % (i, self.local_vars[i]))

        pythonstartup = config.options.get('shell_file') or os.environ.get('PYTHONSTARTUP')

        if preferred_interface := config.options.get('shell_interface'):
            shells_to_try = [preferred_interface, 'python']
        else:
            shells_to_try = SHELLS

        for shell in shells_to_try:
            try:
                shell_func = getattr(self, shell)
                return shell_func(self.local_vars, pythonstartup)
            except ImportError:
                pass
            except Exception:
                _logger.warning("Could not start '%s' shell.", shell)
                _logger.debug("Shell error:", exc_info=True)

    def ipython(self, local_vars, pythonstartup=None):
        from IPython import start_ipython  # noqa: PLC0415
        argv = (
            ['--TerminalIPythonApp.display_banner=False']
            + ([f'--TerminalIPythonApp.exec_files={pythonstartup}'] if pythonstartup else [])
        )
        start_ipython(argv=argv, user_ns=local_vars)

    def ptpython(self, local_vars, pythonstartup=None):
        from ptpython.repl import embed  # noqa: PLC0415
        embed({}, local_vars, startup_paths=[pythonstartup] if pythonstartup else False)

    def bpython(self, local_vars, pythonstartup=None):
        from bpython import embed  # noqa: PLC0415
        embed(local_vars, args=['-q', '-i', pythonstartup] if pythonstartup else None)

    def python(self, local_vars, pythonstartup=None):
        console = Console(local_vars)
        if pythonstartup:
            with open(pythonstartup, encoding='utf-8') as f:
                console.runsource(f.read(), filename=pythonstartup, symbol='exec')
        console.interact(banner='')

    def run(self, cmdargs):
        # Set eventual non-interactive arguments after SEP ('--') as local vars to shell command
        if not self.interactive and SEP in cmdargs:
            idx = cmdargs.index(SEP)
            cmdargs, additional_local_vars = cmdargs[:idx], cmdargs[idx+1:]
            self.local_vars = {
                **self.local_vars,
                'shellargs': additional_local_vars,
            }

        # Parse the configuration
        config.parse_config(cmdargs, setup_logging=self.interactive)

        dbnames = config['db_name']
        if len(dbnames) > 1:
            Command.die("-d/--database/db_name has multiple database, please provide a single one")
        db_name = (dbnames or [None])[0]
        if self.interactive:
            cli_server.report_configuration()

        # Start the server
        server.start(preload=[], stop=True)

        # Trap SIGINT
        def raise_keyboard_interrupt(*a):
            raise KeyboardInterrupt()
        signal.signal(signal.SIGINT, raise_keyboard_interrupt)

        def start():
            if self.interactive:
                self.console()
            else:
                self._execute()

        # Start the console
        if not db_name:
            start()
        else:
            threading.current_thread().dbname = db_name
            with closing(Registry(db_name).cursor()) as cr:
                ctx = Environment(cr, SUPERUSER_ID, {})['res.users'].context_get()
                env = Environment(cr, SUPERUSER_ID, ctx)
                self.local_vars = {
                    **self.local_vars,
                    'env': env,
                    'self': env.user,
                }
                start()
