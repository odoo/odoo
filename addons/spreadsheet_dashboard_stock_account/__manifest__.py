# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for stock",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'stock_account'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['stock_account'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
