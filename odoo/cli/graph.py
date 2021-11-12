# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import fnmatch
import logging
import optparse
import sys
from itertools import cycle, product

from . import Command
import odoo
from odoo.modules.registry import Registry
from odoo.orm.models import MAGIC_COLUMNS

_logger = logging.getLogger(__name__)
STYLE = cycle(product(
    ['DarkOliveGreen', 'DarkMagenta', 'DarkSlateBlue', 'DodgerBlue', 'Black', 'GoldenRod'],
    ['solid', 'dashed', 'dotted'],
))

# usage: odoo/odoo-bin graph --addons-path=odoo/addons,enterprise -d master --models="ir.*" -o ~/classes.dot && xdot ~/classes.dot
# one can also convert to SVG: dot -Tsvg ~/classes.dot > ~/classes.svg

class Graph(Command):
    def run(self, args):
        parser = odoo.tools.config.parser
        group = optparse.OptionGroup(parser, "Graph Configuration")
        group.add_option("--models",
                         dest='graph_models',
                         help="Comma separated list of model or pattern (fnmatch)")
        group.add_option("--out", "-o",
                         dest='out_file',
                         help="Output file")
        parser.add_option_group(group)
        opt = odoo.tools.config.parse_config(args)
        graph_models = opt.graph_models and set(opt.graph_models.split(','))
        out_file = opt.out_file
        if not out_file:
            parser.error("Must provide the output file as --out or -o")
        dbnames = odoo.tools.config['db_name']
        if not dbnames:
            _logger.error('Graph command needs a database name. Use "-d" argument')
            sys.exit(1)
        if len(dbnames) > 1:
            sys.exit("-d/--database/db_name has multiple database, please provide a single one")
        dbname = dbnames[0]
        registry = Registry(dbname)
        with registry.cursor() as cr:
            with open(out_file, 'w+') as file:
                file.write(
                    'digraph "classes" {\n'
                    'charset="utf-8"\n'
                    'layout="fdp"\n'
                    'splines=polyline\n'
                    'sep="+10,10"\n'
                )
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                model_to_id = set()
                relations = set()
                for model in env.values():
                    if graph_models and not any(fnmatch.fnmatch(model._name, match) for match in graph_models):
                        continue
                    model_name = model._name.replace('.', '_')
                    model_to_id.add(model_name)
                    fields = []
                    for field in model._fields.values():
                        name_color = (
                            'lightgreen' if field.related else
                            'lightblue' if field.compute else
                            'white'
                        )
                        type_color = 'lightgray' if field.store else 'white'
                        field_type = field.type
                        if field.required:
                            field_type = f'<B>{field_type}</B>'
                        if field.readonly:
                            field_type = f'<I>{field_type}</I>'
                        if field.name in MAGIC_COLUMNS or field.inherited:
                            pass
                        elif field.relational:
                            fields.append(f'<TR><TD BGCOLOR="{name_color}" PORT="{field.name}">{field.name}</TD><TD BGCOLOR="{type_color}">{field_type}</TD><TD>{field.comodel_name}</TD></TR>')
                            relations.add(field)
                        else:
                            fields.append(f'<TR><TD BGCOLOR="{name_color}">{field.name}</TD><TD BGCOLOR="{type_color}">{field_type}</TD></TR>')
                    fields = '\n'.join(fields)
                    label = '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">' + f"""
                        <TR><TD COLSPAN="3" BGCOLOR="yellow">{model._name}</TD></TR>
                        <TR><TD COLSPAN="3" BGCOLOR="lightyellow">{model._description}</TD></TR>
                        {fields}
                    """ + '</TABLE>'
                    file.write(f'{model_name}[label=<{label}>, shape="none", margin=0];\n')
                for field in list(relations):
                    if getattr(field, 'inverse_name', None):
                        inverse = env[field.comodel_name]._fields[field.inverse_name]
                        if inverse in relations:
                            relations.remove(inverse)
                for field in relations:
                    from_ = field.model_name.replace('.', '_')
                    to = field.comodel_name.replace('.', '_')
                    field_to = getattr(field, 'inverse_name', None)
                    if from_ in model_to_id and to in model_to_id:
                        color, style = next(STYLE)
                        if field_to:
                            file.write(f'{from_}:{field.name}:w -> {to}:{field_to}:w [dir="both" arrowhead="normal", arrowtail="normal", style="{style}", color="{color}"];\n')
                        else:
                            file.write(f'{from_}:{field.name}:w -> {to}:n [arrowhead="normal", arrowtail="none", style="{style}", color="{color}"];\n')
                file.write('}')
