# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for restaurants",
    'version': '1.0',
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'pos_hr', 'pos_restaurant'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['pos_hr', 'pos_restaurant'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
