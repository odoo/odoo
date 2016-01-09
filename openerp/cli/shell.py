# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import argparse
import code
import os
import signal
import sys

import openerp
from . import Command

def raise_keyboard_interrupt(*a):
    raise KeyboardInterrupt()

class Console(code.InteractiveConsole):
    def __init__(self, locals=None, filename="<console>"):
        code.InteractiveConsole.__init__(self, locals, filename)
        try:
            import readline
            import rlcompleter
        except ImportError:
            print 'readline or rlcompleter not available, autocomplete disabled.'
        else:
            readline.set_completer(rlcompleter.Completer(locals).complete)
            readline.parse_and_bind("tab: complete")

class Shell(Command):
    """Start odoo in an interactive shell"""
    def init(self, args):
        openerp.tools.config.parse_config(args)
        openerp.cli.server.report_configuration()
        openerp.service.server.start(preload=[], stop=True)
        signal.signal(signal.SIGINT, raise_keyboard_interrupt)

    def console(self, local_vars):
        if not os.isatty(sys.stdin.fileno()):
            exec sys.stdin in local_vars
        else:
            if 'env' not in local_vars:
                print 'No environment set, use `odoo.py shell -d dbname` to get one.'
            for i in sorted(local_vars):
                print '%s: %s' % (i, local_vars[i])
            Console(locals=local_vars).interact()

    def shell(self, dbname):
        local_vars = {
            'openerp': openerp
        }
        with openerp.api.Environment.manage():
            if dbname:
                registry = openerp.modules.registry.RegistryManager.get(dbname)
                with registry.cursor() as cr:
                    uid = openerp.SUPERUSER_ID
                    ctx = openerp.api.Environment(cr, uid, {})['res.users'].context_get()
                    env = openerp.api.Environment(cr, uid, ctx)
                    local_vars['env'] = env
                    local_vars['self'] = env.user
                    self.console(local_vars)
            else:
                self.console(local_vars)

    def run(self, args):
        self.init(args)
        self.shell(openerp.tools.config['db_name'])
        return 0

class IPShell(Shell):
    """Start Odoo in an IPython shell or kernel"""
    def console(self, local_vars):
        import IPython
        if self.kernel:
            IPython.start_kernel(argv=[], user_ns=local_vars)
        else:
            IPython.start_ipython(argv=[], user_ns=local_vars)

    def init(self, cmdargs):
        parser = argparse.ArgumentParser(
            prog="%s ipshell" % sys.argv[0].split(os.path.sep)[-1],
            description=self.__doc__
        )
        parser.add_argument('--kernel', action='store_true',
            help='Start a kernel instance')
        args, unknown_cmdargs = parser.parse_known_args(cmdargs)
        self.kernel = args.kernel

        super(IPShell, self).init(unknown_cmdargs)
