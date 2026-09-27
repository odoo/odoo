# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for restaurants",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'pos_hr', 'pos_restaurant'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['pos_hr', 'pos_restaurant'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
