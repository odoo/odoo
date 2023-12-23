# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Spreadsheet Dashboard for Timesheets Billing Rate',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Access a dashboard with analytics about the billing rate of your timesheets.',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'sale_timesheet'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['sale_timesheet'],
    'license': 'LGPL-3',
}
