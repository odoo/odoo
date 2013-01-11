"""
Display information about a given model.
"""
import os
import sys
import textwrap

def run(args):
    assert args.database
    assert args.model
    import openerp
    openerp.tools.config['log_level'] = 100
    openerp.netsvc.init_logger()
    registry = openerp.modules.registry.RegistryManager.get(
        args.database, update_module=False)
    model = registry.get(args.model)
    longest_k = 1
    longest_string = 1
    columns = model._columns

    if args.field and args.field not in columns:
        print "No such field."
        sys.exit(1)
        
    if args.field:
        columns = { args.field: columns[args.field] }
    else:
        print "Fields (model `%s`, database `%s`):" % (args.model, args.database)

    for k, v in columns.items():
        longest_k = len(k) if longest_k < len(k) else longest_k
        longest_string = len(v.string) \
            if longest_string < len(v.string) else longest_string
    for k, v in sorted(columns.items()):
        attr = []
        if v.required:
            attr.append("Required")
        if v.readonly:
            attr.append("Read-only")
        attr = '/'.join(attr)
        attr = '(' + attr + ')' if attr else attr
        if args.verbose:
            print v.string, '-- ' + k + ', ' + v._type, attr
        else:
            print k.ljust(longest_k + 2), v._type, attr
        if args.verbose and v.help:
            print textwrap.fill(v.help, initial_indent='    ', subsequent_indent='    ')

def add_parser(subparsers):
    parser = subparsers.add_parser('model',
        description='Display information about a given model for an existing database.')
    parser.add_argument('-d', '--database', metavar='DATABASE', required=True,
        help='the database to connect to')
    parser.add_argument('-m', '--model', metavar='MODEL', required=True,
        help='the model for which information should be displayed')
    parser.add_argument('-v', '--verbose', action='store_true',
        help='display more information')
    parser.add_argument('-f', '--field', metavar='FIELD',
        help='display information only for this particular field')

    parser.set_defaults(run=run)
