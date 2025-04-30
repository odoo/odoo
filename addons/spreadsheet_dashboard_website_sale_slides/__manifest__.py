# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for eLearning",
    'version': '1.0',
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'website_sale_slides'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['website_sale_slides'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
