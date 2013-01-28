"""
Install OpenERP on a new (by default) database.
"""
import os
import sys

import common

# TODO turn template1 in a parameter
# This should be exposed from openerp (currently in
# openerp/service/web_services.py).
def create_database(database_name):
    import openerp
    db = openerp.sql_db.db_connect('template1')
    cr = db.cursor() # TODO `with db as cr:`
    try:
        cr.autocommit(True)
        cr.execute("""CREATE DATABASE "%s"
            ENCODING 'unicode' TEMPLATE "template1" """ \
            % (database_name,))
    finally:
        cr.close()

def run(args):
    assert args.database
    assert args.module

    import openerp

    config = openerp.tools.config
    config['log_handler'] = [':CRITICAL']
    if args.addons:
        args.addons = args.addons.split(':')
    else:
        args.addons = []
    config['addons_path'] = ','.join(args.addons)
    openerp.netsvc.init_logger()

    # Install the import hook, to import openerp.addons.<module>.
    openerp.modules.module.initialize_sys_path()
    openerp.modules.loading.open_openerp_namespace()

    registry = openerp.modules.registry.RegistryManager.get(
        args.database, update_module=False)

    ir_module_module = registry.get('ir.module.module')
    cr = registry.db.cursor() # TODO context manager
    try:
        ids = ir_module_module.search(cr, openerp.SUPERUSER_ID, [('name', 'in', args.module), ('state', '=', 'installed')], {})
        if len(ids) == len(args.module):
            ir_module_module.button_immediate_uninstall(cr, openerp.SUPERUSER_ID, ids, {})
        else:
            print "At least one module not found (database `%s`)." % (args.database,)
    finally:
        cr.close()

def add_parser(subparsers):
    parser = subparsers.add_parser('uninstall',
        description='Uninstall some modules from an OpenERP database.')
    parser.add_argument('-d', '--database', metavar='DATABASE',
        **common.required_or_default('DATABASE', 'the database to modify'))
    common.add_addons_argument(parser)
    parser.add_argument('--module', metavar='MODULE', action='append',
        help='specify a module to uninstall'
        ' (this option can be repeated)')

    parser.set_defaults(run=run)
