# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Test Main Flow',
    'category': 'Hidden/Tests',
    'description': """
This module will test the main workflow of Odoo.
It will install some main apps and will try to execute the most important actions.
""",
    'depends': ['web_tour', 'crm', 'sale_timesheet', 'purchase_stock', 'mrp', 'account'],
    'post_init_hook': '_auto_install_enterprise_dependencies',
    'data': ['ir.access.csv'],
    'assets': {
        'web.assets_tests': [
            # inside .
            'test_main_flows/static/tests/tours/*.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
