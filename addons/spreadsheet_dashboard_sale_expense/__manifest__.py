# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for expenses and sales",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['sale_expense', 'spreadsheet_dashboard_hr_expense'],
    'data': [
        "data/dashboards.xml",
    ],
    'demo': [],
    'installable': True,
    'auto_install': ['sale_expense'],
    'license': 'LGPL-3',
    'assets': {}
}
