"""
Update an existing OpenERP database.
"""

def run(args):
    assert args.database
    import openerp
    config = openerp.tools.config
    config['update']['all'] = 1
    openerp.modules.registry.RegistryManager.get(
        args.database, update_module=True)

def add_parser(subparsers):
    parser = subparsers.add_parser('update',
        description='Update an existing OpenERP database.')
    parser.add_argument('-d', '--database', metavar='DATABASE', required=True,
        help='the database to update')

    parser.set_defaults(run=run)
