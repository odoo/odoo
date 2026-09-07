# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spreadsheet Dashboard for Timesheets Billing Rate',
    'category': 'Productivity/Dashboard',
    'summary': 'Access a dashboard with analytics about the billing rate of your timesheets.',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'sale_timesheet'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['sale_timesheet'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
