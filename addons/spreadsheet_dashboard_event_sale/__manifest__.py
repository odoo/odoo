# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for events",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['event_sale', 'spreadsheet_dashboard_sale'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['event_sale'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
