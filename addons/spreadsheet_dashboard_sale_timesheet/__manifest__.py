# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spreadsheet Dashboard for Timesheets Billing Rate',
    'version': '1.0',
    'category': 'Services/Spreadsheet',
    'summary': 'Access a dashboard with analytics about the billing rate of your timesheets.',
    'description': 'Access a dashboard with analytics about the billing rate of your timesheets.',
    'depends': ['spreadsheet_dashboard', 'sale_timesheet'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['sale_timesheet'],
    'license': 'LGPL-3',
}
