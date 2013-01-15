"""
Read a record.
"""
import os
import sys
import textwrap

# TODO provide a --rpc flag to use XML-RPC (with a specific username) instead
# of server-side library.
def run(args):
    assert args.database
    assert args.model
    import openerp
    config = openerp.tools.config
    config['log_handler'] = [':CRITICAL']
    openerp.netsvc.init_logger()
    registry = openerp.modules.registry.RegistryManager.get(
        args.database, update_module=False)
    model = registry.get(args.model)
    cr = registry.db.cursor() # TODO context manager
    field_names = [args.field] if args.field else []
    if args.short:
        # ignore --field
        field_names = ['name']
    try:
        xs = model.read(cr, 1, args.id, field_names, {})
    finally:
        cr.close()

    if xs:
        print "Records (model `%s`, database `%s`):" % (args.model, args.database)
        x = xs[0]
        if args.short:
            print str(x['id']) + '.', x['name']
        else:
            longest_k = 1
            for k, v in x.items():
                longest_k = len(k) if longest_k < len(k) else longest_k
            for k, v in sorted(x.items()):
                print (k + ':').ljust(longest_k + 2), v
    else:
        print "Record not found."

def add_parser(subparsers):
    parser = subparsers.add_parser('read',
        description='Display a record.')
    parser.add_argument('-d', '--database', metavar='DATABASE', required=True,
        help='the database to connect to')
    parser.add_argument('-m', '--model', metavar='MODEL', required=True,
        help='the model for which a record should be read')
    parser.add_argument('-i', '--id', metavar='RECORDID', required=True,
        help='the record id')
    parser.add_argument('-v', '--verbose', action='store_true',
        help='display more information')
    parser.add_argument('--short', action='store_true',
        help='display less information')
    parser.add_argument('-f', '--field', metavar='FIELD',
        help='display information only for this particular field')

    parser.set_defaults(run=run)
