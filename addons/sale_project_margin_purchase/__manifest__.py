# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Margins in Projects - Purchase',
    'summary': 'Adds the purchase order lines to the project profitability dashboard',
    'category': 'Sales/Sales',
    'depends': ['sale_project_margin', 'project_purchase'],
    'data': [
        'data/dashboards.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
