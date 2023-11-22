# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Test Main Flow',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """
This module will test the main workflow of Odoo.
It will install some main apps and will try to execute the most important actions.
""",
    'depends': ['web_tour', 'crm', 'sale_timesheet', 'purchase_stock', 'mrp', 'account'],
    'installable': True,
    'post_init_hook': '_auto_install_enterprise_dependencies',
    'data': ['models/ir.model.access.csv'],
    'assets': {
        'web.assets_tests': [
            # inside .
            'test_main_flows/static/tests/tours/*.js',
        ],
    },
    'license': 'LGPL-3',
}
