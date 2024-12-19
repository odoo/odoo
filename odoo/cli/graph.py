import sys
from fnmatch import fnmatch
from functools import wraps
from itertools import cycle, product

from . import Command

import odoo
from odoo.modules.registry import Registry
from odoo.orm.models import MAGIC_COLUMNS

""" 
    Create a GraphViz diagram of given models' fields and relations.
    main command:
        odoo/odoo-bin --addons-path=odoo,enterprise graph -d odoodb --models=account.report*
    to visualize: 
        <main_command> | xdot -
    convert to SVG:
        <main_command> | dot -Tsvg > ./classes.svg
"""


COLOR_STYLES = product(
    ['DarkOliveGreen', 'DarkMagenta', 'DarkSlateBlue', 'DodgerBlue', 'Black', 'GoldenRod'],
    ['solid', 'dashed', 'dotted'],
)


def build_env(func):
    @wraps(func)
    def build_env_wrapper(*args, db_name=None, **kwargs):
        with Registry(db_name).cursor() as cr:
            kwargs['env'] = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            return func(*args, **kwargs)
    return build_env_wrapper


class Graph(Command):
    """ Create a GraphViz diagram of given models' fields and relations """

    def run(self, cmdargs):
        self.parser.add_argument('--models', '-m', dest='models', default=None,
            help=(
                "Full names of models to output, the wildcard char '*' can be used, "
                "i.e. 'ir.*'"
            ))
        self.parser.add_argument('--database', '-d', dest='db_name', default=None,
            help="Specify the database name (default to project's directory name")
        self.parser.add_argument('--show_related', dest='show_related', action='store_true',
             help="Show related fields")
        args, _unknown = self.parser.parse_known_args(args=cmdargs)
        if not args.models or not args.db_name:
            self.parser.print_help()
            sys.exit()
        args.db_name = args.db_name.split(',')
        if len(args.db_name) > 1:
            self.parser.print_help()
            sys.exit("--database/-d has multiple databases, please provide a single one")
        args.db_name = args.db_name[0]
        model_patterns = args.models and set(args.models.split(','))

        self.export_graph(model_patterns, db_name=args.db_name, show_related=args.show_related)

    @build_env
    def export_graph(self, model_patterns, show_related=False, env=None):
        def print_indented(s, initial=12, **kwargs):
            for idx, line in enumerate(line for line in s.splitlines() if line.lstrip()):
                print(line[initial:], **kwargs)
        def tag(name, s):
            return f'<{name}>{s}</{name}>'
        def replacedot(name):
            return name.replace('.', '_')

        print_indented("""
            digraph "classes" {
                charset="utf-8"
                layout="fdp"
                splines=polyline
                sep="+10,10"
        """)
        relations = set()
        matching_models = {
            model_name.replace('.', '_'): model for model_name, model in env.items()
            if any(fnmatch(model_name, pattern) for pattern in model_patterns)
        }
        for model_name, model in matching_models.items():
            print_indented(f"""
                {model_name}[label=<
                    <table border="0" cellborder="1" cellspacing="0">
                        <tr><td colspan="3" bgcolor="yellow">{model._name}</td></tr>
                        <tr><td colspan="3" bgcolor="lightyellow">{model._description}</td></tr>
            """)

            fields = [
                field 
                for name, field in model._fields.items()
                if name not in MAGIC_COLUMNS
                    and not ((field.related or field.inherited) and not show_related)
            ]
            for field in fields:
                name_color = (
                    'lightgreen' if field.related else
                    'lightblue' if field.compute else
                    'white'
                )
                type_color = 'lightgray' if field.store else 'white'
                field_str = field.type
                if field.required:
                    field_str = tag('b', field_str)
                if field.readonly:
                    field_str = tag('i', field_str)
                if field.relational:
                    print_indented(f"""
                        <tr>
                            <td bgcolor="{name_color}" port="{field.name}">{field.name}</td>
                            <td bgcolor="{type_color}">{field_str}</td>
                            <td>{field.comodel_name}</td>
                        </tr>
                    """)
                    if replacedot(field.comodel_name) in matching_models:
                        inverse_name = getattr(field, 'inverse_name', '')
                        relations.add((
                            field,
                            replacedot(field.model_name),
                            replacedot(field.comodel_name),
                            replacedot(inverse_name),
                        ))
                else:
                    print_indented(f"""
                        <tr>
                            <td bgcolor="{name_color}">{field.name}</td>
                            <td bgcolor="{type_color}">{field_str}</td>
                        </tr>
                    """)
            print_indented("""
                    </table>
                >, shape="none", margin=0];
            """)

        for (field, model_from, model_to, inverse_name), (color, style) in zip(relations, cycle(COLOR_STYLES)):
            print_indented(f"""
                {model_from}:{field.name}:w -> 
            """, end='')
            if inverse_name:
                direction, target = (', dir="both"', f'{model_to}:{inverse_name}:w')
            else:
                direction, target = ('', f'{model_to}:n')
            print(f'{target} [arrowhead="normal", arrowtail="normal", style="{style}", color="{color}"{direction}];')

        print_indented("""
            }
        """)
