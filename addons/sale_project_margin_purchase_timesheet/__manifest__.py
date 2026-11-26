# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Margins in Projects - Purchase + Timesheet',
    'summary': 'Project profitability dashboard combining: purchase, timesheet',
    'category': 'Sales/Sales',
    'depends': ['sale_project_margin_purchase', 'sale_timesheet_margin'],
    'data': [
        'data/dashboards.xml',
    ],
    'auto_install': ['sale_project_margin_purchase', 'sale_timesheet_margin'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
