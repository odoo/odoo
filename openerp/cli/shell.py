# -*- coding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import code
import signal

import openerp
from . import Command

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
        self.locals = {
            'openerp': openerp
        }

    def shell(self, dbname):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        # TODO: Fix ctrl-c that doesnt seem to generate KeyboardInterrupt
        with openerp.api.Environment.manage():
            if dbname:
                registry = openerp.modules.registry.RegistryManager.get(dbname)
                with registry.cursor() as cr:
                    uid = openerp.SUPERUSER_ID
                    ctx = openerp.api.Environment(cr, uid, {})['res.users'].context_get()
                    env = openerp.api.Environment(cr, uid, ctx)
                    self.locals['env'] = env
                    self.locals['self'] = env.user
                    print 'Connected to %s,' % dbname
                    print '  env: Environement(cr, openerp.SUPERUSER_ID, %s).' % ctx
                    print '  self: %s.' % env.user
                    Console(locals=self.locals).interact()
            else:
                print 'No evironement set, use `odoo.py shell -d dbname` to get one.'
                Console(locals=self.locals).interact()

    def run(self, args):
        self.init(args)
        self.shell(openerp.tools.config['db_name'])
        return 0

