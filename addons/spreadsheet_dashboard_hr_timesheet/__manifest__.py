# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Spreadsheet Dashboard for Timesheets',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Access a dashboard with analytics about your timesheets.',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'hr_timesheet'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['hr_timesheet'],
    'license': 'LGPL-3',
}
