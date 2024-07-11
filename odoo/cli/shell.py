# Part of Odoo. See LICENSE file for full copyright and licensing details.
import code
import logging
import os
import signal
import sys
from pathlib import Path

import odoo
from odoo.tools import config
from . import Command

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
    raise KeyboardInterrupt()


class Console(code.InteractiveConsole):
    def __init__(self, locals=None, filename="<console>"):
        code.InteractiveConsole.__init__(self, locals, filename)
        try:
            import readline
            import rlcompleter
        except ImportError:
            print('readline or rlcompleter not available, autocomplete disabled.')
        else:
            readline.set_completer(rlcompleter.Completer(locals).complete)
            readline.parse_and_bind("tab: complete")


class Shell(Command):
    """Start odoo in an interactive shell"""
    supported_shells = ['ipython', 'ptpython', 'bpython', 'python']

    def init(self, args):
        config.parser.prog = f'{Path(sys.argv[0]).name} {self.name}'
        config.parse_config(args)
        odoo.cli.server.report_configuration()
        odoo.service.server.start(preload=[], stop=True)
        signal.signal(signal.SIGINT, raise_keyboard_interrupt)

    def console(self, local_vars):
        if not os.isatty(sys.stdin.fileno()):
            local_vars['__name__'] = '__main__'
            exec(sys.stdin.read(), local_vars)
        else:
            if 'env' not in local_vars:
                print('No environment set, use `%s shell -d dbname` to get one.' % sys.argv[0])
            for i in sorted(local_vars):
                print('%s: %s' % (i, local_vars[i]))

            preferred_interface = config.options.get('shell_interface')
            if preferred_interface:
                shells_to_try = [preferred_interface, 'python']
            else:
                shells_to_try = self.supported_shells

            for shell in shells_to_try:
                try:
                    return getattr(self, shell)(local_vars)
                except ImportError:
                    pass
                except Exception:
                    _logger.warning("Could not start '%s' shell." % shell)
                    _logger.debug("Shell error:", exc_info=True)

    def ipython(self, local_vars):
        from IPython import start_ipython
        start_ipython(argv=[], user_ns=local_vars)

    def ptpython(self, local_vars):
        from ptpython.repl import embed
        embed({}, local_vars)

    def bpython(self, local_vars):
        from bpython import embed
        embed(local_vars)

    def python(self, local_vars):
        Console(locals=local_vars).interact()

    def shell(self, dbname):
        local_vars = {
            'openerp': odoo,
            'odoo': odoo,
        }
        if dbname:
            registry = odoo.registry(dbname)
            with registry.cursor() as cr:
                uid = odoo.SUPERUSER_ID
                ctx = odoo.api.Environment(cr, uid, {})['res.users'].context_get()
                env = odoo.api.Environment(cr, uid, ctx)
                local_vars['env'] = env
                local_vars['self'] = env.user
                self.console(local_vars)
                cr.rollback()
        else:
            self.console(local_vars)

    def run(self, args):
        self.init(args)
        self.shell(config['db_name'])
        return 0
