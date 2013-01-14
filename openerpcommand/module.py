"""
Show module information for a given database or from the file-system.
"""
import os
import sys
import textwrap

from . import common

# TODO provide a --rpc flag to use XML-RPC (with a specific username) instead
# of server-side library.
def run(args):
    assert args.database
    import openerp

    config = openerp.tools.config
    config['log_handler'] = [':CRITICAL']
    if args.addons:
        args.addons = args.addons.split(':')
    else:
        args.addons = []
    config['addons_path'] = ','.join(args.addons)
    openerp.netsvc.init_logger()

    if args.filesystem:
        module_names = common.get_addons_from_paths(args.addons, [])
        print "Modules (addons path %s):" % (', '.join(args.addons),)
        for x in sorted(module_names):
            print x
    else:
        registry = openerp.modules.registry.RegistryManager.get(
            args.database, update_module=False)
 
        xs = []
        ir_module_module = registry.get('ir.module.module')
        cr = registry.db.cursor() # TODO context manager
        try:
            ids = ir_module_module.search(cr, openerp.SUPERUSER_ID, [], {})
            xs = ir_module_module.read(cr, openerp.SUPERUSER_ID, ids, [], {})
        finally:
            cr.close()
 
        if xs:
            print "Modules (database `%s`):" % (args.database,)
            for x in xs:
                if args.short:
                    print '%3d %s' % (x['id'], x['name'])
                else:
                    print '%3d %s %s' % (x['id'], x['name'], {'installed': '(installed)'}.get(x['state'], ''))
        else:
            print "No module found (database `%s`)." % (args.database,)

def add_parser(subparsers):
    parser = subparsers.add_parser('module',
        description='Display modules known from a given database or on file-system.')
    parser.add_argument('-d', '--database', metavar='DATABASE',
        **common.required_or_default('DATABASE', 'the database to modify'))
    common.add_addons_argument(parser)
    parser.add_argument('-m', '--module', metavar='MODULE', required=False,
        help='the module for which information should be shown')
    parser.add_argument('-v', '--verbose', action='store_true',
        help='display more information')
    parser.add_argument('--short', action='store_true',
        help='display less information')
    parser.add_argument('-f', '--filesystem', action='store_true',
        help='display module in the addons path, not in db')

    parser.set_defaults(run=run)
