# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for time sheets",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['sale_timesheet', 'spreadsheet_dashboard_hr_timesheet', 'spreadsheet_dashboard_sale'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['sale_timesheet'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
