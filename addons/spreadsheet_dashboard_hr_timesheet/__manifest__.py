# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for time sheets",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'hr_timesheet'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['hr_timesheet'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
