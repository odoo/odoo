# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for point of sale",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'point_of_sale'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['point_of_sale'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
