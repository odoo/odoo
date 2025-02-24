# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spreadsheet Dashboard for Timesheets',
    'version': '1.0',
    'category': 'Services/Spreadsheet',
    'summary': 'Access a dashboard with analytics about your timesheets.',
    'description': 'Access a dashboard with analytics about your timesheets.',
    'depends': ['spreadsheet_dashboard', 'hr_timesheet'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['hr_timesheet'],
    'license': 'LGPL-3',
}
