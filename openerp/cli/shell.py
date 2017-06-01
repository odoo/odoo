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

from __future__ import print_function
from code import InteractiveConsole
from pprint import pprint
import sys

from . import Command
import openerp
from openerp.api import Environment


class Console(InteractiveConsole):

    def __init__(self, locals=None, filename="<console>"):
        InteractiveConsole.__init__(self, locals, filename)
        try:
            import readline
            import rlcompleter
        except ImportError:
            print('Autocomplete not available: '
                  'readline or rlcompleter not available.')
        else:
            readline.set_completer(rlcompleter.Completer(locals).complete)
            readline.parse_and_bind("tab: complete")


def interactive_shell():

    dbname = openerp.tools.config['db_name']
    registry = openerp.modules.registry.RegistryManager.get(dbname)

    with openerp.api.Environment.manage():
        with registry.cursor() as cr:
            uid = openerp.SUPERUSER_ID
            ctx = Environment(cr, uid, {})['res.users'].context_get()
            env = Environment(cr, uid, ctx)
            print('Connected to %s, with `self` mapped to %s.'
                  % (dbname, env.user))
            Console(locals={
                'env': env,
                'self': env.user,
                'pp': pprint,
                'pprint': pprint}
            ).interact()


def main(args):
    openerp.tools.config.parse_config(args)
    openerp.cli.server.report_configuration()
    rc = openerp.service.server.start(preload=[], stop=True)
    interactive_shell()
    sys.exit(rc)


class Shell(Command):
    """Start odoo in an interactive shell"""
    def run(self, args):
        main(args)
