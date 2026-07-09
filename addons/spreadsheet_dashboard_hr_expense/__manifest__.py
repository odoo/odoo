# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for expenses",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['sale_expense', 'spreadsheet_dashboard_sale'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['sale_expense'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
