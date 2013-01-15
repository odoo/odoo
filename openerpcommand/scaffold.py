"""
Generate an OpenERP module skeleton.
"""

import os
import sys

def run(args):
    assert args.module
    module = args.module

    if os.path.exists(module):
        print "The path `%s` already exists."
        sys.exit(1)

    os.mkdir(module)
    os.mkdir(os.path.join(module, 'models'))
    with open(os.path.join(module, '__openerp__.py'), 'w') as h:
        h.write(MANIFEST)
    with open(os.path.join(module, '__init__.py'), 'w') as h:
        h.write(INIT_PY)
    with open(os.path.join(module, 'models', '__init__.py'), 'w') as h:
        h.write(MODELS_PY % (module,))

def add_parser(subparsers):
    parser = subparsers.add_parser('scaffold',
        description='Generate an OpenERP module skeleton.')
    parser.add_argument('module', metavar='MODULE',
        help='the name of the generated module')

    parser.set_defaults(run=run)

MANIFEST = """\
# -*- coding: utf-8 -*-
{
    'name': '<Module name>',
    'version': '0.0',
    'category': '<Category>',
    'description': '''
<Long description>
''',
    'author': '<author>',
    'maintainer': '<maintainer>',
    'website': 'http://<website>',
    # Add any module that are necessary for this module to correctly work in
    # the `depends` list.
    'depends': ['base'],
    'data': [
    ],
    'test': [
    ],
    # Set to False if you want to prevent the module to be known by OpenERP
    # (and thus appearing in the list of modules).
    'installable': True,
    # Set to True if you want the module to be automatically whenever all its
    # dependencies are installed.
    'auto_install': False,
}
"""

INIT_PY = """\
# -*- coding: utf-8 -*-
import models
"""

MODELS_PY = """\
# -*- coding: utf-8 -*-
import openerp

# Define a new model.
class my_model(openerp.osv.osv.Model):

    _name = '%s.my_model'

    _columns = {
    }
"""
