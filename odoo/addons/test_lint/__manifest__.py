# -*- coding: utf-8 -*-
{
    'name': 'test-lint',
    'version': '0.1',
    'category': 'Hidden/Tests',
    'description': """A module to test Odoo code with various linters.""",
    'depends': ['base'],
    'external_dependencies': {
        'python': ['astroid', 'pylint'],
    },
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
