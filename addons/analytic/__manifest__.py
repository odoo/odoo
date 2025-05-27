# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Analytic Accounting',
    'version': '1.2',
    'category': 'Accounting/Accounting',
    'depends' : ['base', 'mail', 'uom'],
    'description': """
Module for defining analytic accounting object.
===============================================

In Odoo, analytic accounts are linked to general accounts but are treated
totally independently. So, you can enter various different analytic operations
that have no counterpart in the general financial accounts.
    """,
    'data': [
        'security/analytic_security.xml',
        'security/ir.model.access.csv',
        'views/analytic_line_views.xml',
        'views/analytic_account_views.xml',
        'views/analytic_plan_views.xml',
        'views/analytic_distribution_model_views.xml',
        'data/analytic_data.xml'
    ],
    'demo': [
        'data/analytic_account_demo.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'analytic/static/src/components/**/*',
            'analytic/static/src/services/**/*',
            'analytic/static/src/views/**/*',
            ('remove', 'analytic/static/src/views/graph/**'),
            ('remove', 'analytic/static/src/views/pivot/**'),
        ],
        'web.assets_backend_lazy': [
            'analytic/static/src/views/graph/**',
            'analytic/static/src/views/pivot/**',
        ],
        'web.assets_unit_tests': [
            'analytic/static/tests/**/*',
        ],
    },
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
