# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for restaurant with HR",
    'category': 'Productivity/Dashboard',
    'summary': 'Restaurant with HR Spreadsheet Dashboard',
    'depends': ['spreadsheet_dashboard_pos_restaurant', 'pos_hr'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['pos_hr'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
