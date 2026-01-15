# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for time sheets",
    'version': '1.0',
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'sale_timesheet'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['sale_timesheet'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
