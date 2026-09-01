# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spreadsheet Dashboard for Timesheets',
    'category': 'Productivity/Dashboard',
    'summary': 'Dashboard with timesheet analytics.',
    'description': 'Access a dashboard with analytics about your timesheets.',
    'depends': ['spreadsheet_dashboard', 'hr_timesheet'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['hr_timesheet'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
