# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#pylint: disable=import-outside-toplevel

from __future__ import print_function
import code
import logging
import optparse
import os
import signal
import sys

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
    def __init__(self, local_vars=None, filename="<console>"):
        code.InteractiveConsole.__init__(self, local_vars, filename)
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
    supported_shells = ['ipython', 'ptpython', 'bpython', 'python']

    def init(self, args):
        parser = config.parser

        # Only display those options when running odoo-bin shell --help
        group = optparse.OptionGroup(parser, "Shell options")
        group.add_option('--shell-file', dest='shell_file', type="string",
                         help="Specify a python script to be run after the start of the shell mode.")
        group.add_option('--shell-interface', dest='shell_interface', type="string",
                         help="Specify a preferred REPL to use in shell mode. Supported REPLs are: "
                              "[ipython|ptpython|bpython|python]")
        parser.add_option_group(group)

        config.parse_config(args)
        odoo.cli.server.report_configuration()
        odoo.service.server.start(preload=[], stop=True)
        signal.signal(signal.SIGINT, raise_keyboard_interrupt)

    def _compile_file(self, filename):
        if filename and os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return compile(f.read(), filename, "exec")
        return None

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
        from traitlets.config.loader import Config
        # https://ipython.org/ipython-doc/3/config/intro.html
        ipython_config = None
        if config.get('shell_file') and os.path.exists(config['shell_file']):
            ipython_config = Config()
            ipython_config.InteractiveShellApp.exec_files = [config['shell_file']]
        start_ipython(argv=[], user_ns=local_vars, config=ipython_config)

    def ptpython(self, local_vars):
        from ptpython.repl import embed
        # https://github.com/prompt-toolkit/ptpython/tree/master/ptpython/repl.py#L656
        code = self._compile_file(config.get('shell_file'))
        def configure(repl):
            if code:
                exec(code, repl.get_globals(), repl.get_locals())
        embed({}, local_vars, configure=configure)

    def bpython(self, local_vars):
        from bpython import embed
        args = None
        # https://github.com/bpython/bpython/blob/master/bpython/__init__.py#L39
        if config.get('shell_file') and os.path.exists(config['shell_file']):
            args = ["-i", config['shell_file']]
        embed(local_vars, args=args)

    def python(self, local_vars):
        console = Console(local_vars)
        # https://docs.python.org/3/library/code.html#code.InteractiveInterpreter.runcode
        code = self._compile_file(config.get('shell_file'))
        if code:
            console.runcode(code)
        console.interact()

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
