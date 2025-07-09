import code
import logging
import os
import signal
import sys
import threading
from contextlib import contextmanager

import odoo  # to expose in the shell
from odoo.api import SUPERUSER_ID, Environment
from odoo.modules.registry import Registry
from odoo.service import server
from odoo.tools import config

from . import Command
from . import server as cli_server

_logger = logging.getLogger(__name__)
SHELLS = ['ipython', 'ptpython', 'bpython', 'python']


""" Exit behaviors
    ==============

    shell    | ^D    | exit() | quit() | sys.exit() | raise SystemExit()
    ----------------------------------------------------------------------
    python   | stop  | raise  | raise  | raise      | raise
    ipython  | stop  | stop   | stop   | loop       | loop
    ptpython | stop  | raise  | raise  | raise      | raise
    bpython  | stop  | stop   | stop   | stop       | stop

    stop = The REPL main loop stop.
    raise = Exception raised.
    loop = Stay in REPL.
"""


class Shell(Command):
    """Start odoo in an interactive shell"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument(
            '-c', '--config', dest='config',
            help="use a specific configuration file")
        self.parser.add_argument(
            '-d', '--database', dest='db_name', default=None,
            help="database name, connection details will be taken from the config file")
        self.parser.add_argument(
            '--shell-file', default=os.environ.get('PYTHONSTARTUP'),
            help="Specify a python script to be run after the start of the shell. "
                 "Overrides the env variable PYTHONSTARTUP.")
        self.parser.add_argument(
            '--shell-interface', choices=SHELLS,
            help="Specify a preferred REPL to use in shell mode.")

    @contextmanager
    def _build_env(self, dbname):
        if dbname:
            with Registry(dbname).cursor() as cr:
                ctx = Environment(cr, SUPERUSER_ID, {})['res.users'].context_get()
                env = Environment(cr, SUPERUSER_ID, ctx)
                yield env
                cr.rollback()
        else:
            yield None

    def run(self, cmdargs):
        parsed_args = self.parser.parse_args(args=cmdargs)

        config_args = []
        if parsed_args.config:
            config_args += ['-c', parsed_args.config]
        if parsed_args.db_name:
            config_args += ['-d', parsed_args.db_name]

        config.parse_config(config_args, setup_logging=True)
        cli_server.report_configuration()

        db_names = config['db_name']
        if not db_names:
            _logger.warning("No dbname was specified, Environment won't be available")
        elif len(db_names) > 1:
            self.parser.error("Please provide a single database")
        parsed_args.db_name = next(iter(db_names), None)

        pythonstartup = parsed_args.shell_file or os.environ.get('PYTHONSTARTUP')
        preferred_interface = parsed_args.shell_interface
        shells_to_try = [preferred_interface, 'python'] if preferred_interface else SHELLS

        threading.current_thread().dbname = parsed_args.db_name

        def raise_keyboard_interrupt(*a):
            raise KeyboardInterrupt()
        signal.signal(signal.SIGINT, raise_keyboard_interrupt)
        server.start(preload=[], stop=True)

        local_vars = {
            'openerp': odoo,
            'odoo': odoo,
        }
        with self._build_env(parsed_args.db_name) as env:
            if env:
                local_vars.update({
                    'env': env,
                    'self': env.user,
                })
            else:
                _logger.warning('No environment set, use `%s shell -d dbname` to get one.', sys.argv[0])

            if not os.isatty(sys.stdin.fileno()):
                # If not interactive, read and run the script from stdin
                local_vars['__name__'] = '__main__'
                exec(sys.stdin.read(), local_vars)
                return

            for key, val in sorted(local_vars.items()):
                print(f'{key}: {val}')  # noqa: T201

            for shell in shells_to_try:
                try:
                    shell_func = getattr(self, shell)
                    shell_func(local_vars, pythonstartup)
                    break
                except ImportError:
                    if shell == preferred_interface:
                        _logger.warning("Could not start '%s' shell.", shell)
                except Exception:  # noqa: BLE001
                    _logger.warning("Could not start '%s' shell.", shell)
                    _logger.debug("Shell error:", exc_info=True)

    def ipython(self, local_vars, pythonstartup=None):
        from IPython import start_ipython  # noqa: PLC0415
        argv = [
            '--TerminalIPythonApp.display_banner=False',
            '--TerminalInteractiveShell.confirm_exit=False',
        ]
        if pythonstartup:
            argv.append(f'--TerminalIPythonApp.exec_files={pythonstartup}')
        start_ipython(argv=argv, user_ns=local_vars)

    def ptpython(self, local_vars, pythonstartup=None):
        from ptpython.repl import embed  # noqa: PLC0415

        def configure(repl=None):
            repl.confirm_exit = False
        embed({}, local_vars, configure=configure, startup_paths=[pythonstartup] if pythonstartup else False)

    def bpython(self, local_vars, pythonstartup=None):
        from bpython import embed  # noqa: PLC0415
        embed(local_vars, args=['-q', '-i', pythonstartup] if pythonstartup else None)

    def python(self, local_vars, pythonstartup=None):
        class Console(code.InteractiveConsole):
            def __init__(self, local_vars=None, filename="<console>"):
                """ Initialize the tab completer.
                    This module is not supported on mobile platforms or WebAssembly platforms.
                """
                code.InteractiveConsole.__init__(self, locals=local_vars, filename=filename)
                try:
                    import readline  # noqa: PLC0415
                    import rlcompleter  # noqa: PLC0415
                except ImportError:
                    _logger.warning('readline or rlcompleter not available, autocomplete disabled.')
                else:
                    readline.set_completer(rlcompleter.Completer(local_vars).complete)
                    readline.parse_and_bind("tab: complete")

        console = Console(local_vars)
        if pythonstartup:
            with open(pythonstartup, encoding='utf-8') as f:
                console.runsource(f.read(), filename=pythonstartup, symbol='exec')
        console.interact(banner='')
