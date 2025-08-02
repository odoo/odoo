import code
import logging
import os
import signal
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

import odoo  # to expose in the shell
from odoo.api import SUPERUSER_ID, Environment
from odoo.modules.registry import Registry
from odoo.service import server
from odoo.tools import config

from . import Command
from . import server as cli_server

""" Exit behaviors
    ==============

    shell    | ^D    | exit() | quit() | sys.exit() | raise SystemExit()
    ----------------------------------------------------------------------
    python   | stop  | raise  | raise  | raise      | raise
    ipython  | stop  | stop   | stop   | loop       | loop
    ptpython | stop  | raise  | raise  | raise      | raise
    bpython  | stop  | stop   | stop   | stop       | stop

    Legend:
    stop = The REPL main loop stop.
    raise = Exception raised.
    loop = Stay in REPL.
"""


_logger = logging.getLogger(__name__)
SHELL = ['ipython', 'ptpython', 'bpython', 'python']


class Shell(Command):
    """ Start odoo in an interactive shell """

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
            '--shell-interface', choices=SHELL,
            help="Specify a preferred REPL to use in shell mode.")

    @contextmanager
    def _build_env(self, parsed_args):
        if parsed_args.db_name:
            with Registry(parsed_args.db_name).cursor() as cr:
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

        threading.current_thread().dbname = parsed_args.db_name

        def raise_keyboard_interrupt(*a):
            raise KeyboardInterrupt()
        signal.signal(signal.SIGINT, raise_keyboard_interrupt)

        # Start the server
        server.start(preload=[], stop=True)

        # Gather information from the Environment, if dbname is given
        with self._build_env(parsed_args) as env:

            # Gather information
            local_vars = {
                'openerp': odoo,
                'odoo': odoo,
            }
            if env:
                local_vars.update({
                    'env': env,
                    'self': env.user,
                })

            # If not interactive, read and run the script from stdin
            if not os.isatty(sys.stdin.fileno()):
                local_vars['__name__'] = '__main__'
                exec(sys.stdin.read(), local_vars)
                return None

            # Print the local variables
            for key, val in sorted(local_vars.items()):
                print(f'{key}: {val}')  # noqa: T201

            # Start the shell
            for shell in (
                list({parsed_args.shell_interface, 'python'})
                if parsed_args.shell_interface else SHELL
            ):
                try:
                    shell_func = getattr(self, shell)
                    return shell_func(local_vars, parsed_args)
                except ImportError:
                    pass
                except Exception:  # noqa: BLE001
                    _logger.exception("Could not start '%s' shell", shell)
                    _logger.debug("Shell error:", exc_info=True)
            return None

    def ipython(self, local_vars, parsed_args):
        from IPython import start_ipython  # noqa: PLC0415
        argv = [
            '--TerminalIPythonApp.display_banner=False',
            '--TerminalInteractiveShell.confirm_exit=False',
        ]
        if parsed_args.shell_file:
            argv.append(f'--TerminalIPythonApp.exec_files={parsed_args.shell_file}')
        start_ipython(argv=argv, user_ns=local_vars)

    def ptpython(self, local_vars, parsed_args):
        def configure(repl=None):
            repl.confirm_exit = False
        from ptpython.repl import embed  # noqa: PLC0415
        startup_paths = [parsed_args.shell_file] if parsed_args.shell_file else False
        embed({}, local_vars, configure=configure, startup_paths=startup_paths)

    def bpython(self, local_vars, parsed_args):
        from bpython import embed  # noqa: PLC0415
        args = ['-q', '-i', parsed_args.shell_file] if parsed_args.shell_file else None
        embed(local_vars, args=args)

    def python(self, local_vars, parsed_args):
        class Console(code.InteractiveConsole):
            def __init__(self, *args, **kwargs):
                code.InteractiveConsole.__init__(self, *args, **kwargs)
                self._set_autocompleter()

            def _set_autocompleter(self):
                """ Initialize the tab completer.
                    This module is not supported on mobile platforms or WebAssembly platforms.
                """
                try:
                    import readline  # noqa: PLC0415
                    import rlcompleter  # noqa: PLC0415
                except ImportError:
                    _logger.warning('readline or rlcompleter not available, autocomplete disabled.')
                else:
                    readline.set_completer(rlcompleter.Completer(local_vars).complete)
                    readline.parse_and_bind("tab: complete")

        console = Console(locals=local_vars, filename="<console>")
        if parsed_args.shell_file:
            script = Path(parsed_args.shell_file).read_text(encoding='utf-8')
            console.runsource(script, filename=parsed_args.shell_file, symbol='exec')

        console.interact(banner='')
