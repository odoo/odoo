# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for point of sale",
    'category': 'Productivity/Dashboard',
    'summary': 'point of Sale with HR Spreadsheet Dashboard',
    'depends': ['spreadsheet_dashboard_pos', 'pos_hr'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['pos_hr'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
