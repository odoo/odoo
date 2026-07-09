# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for eLearning",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['website_sale_slides', 'spreadsheet_dashboard_website_sale'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['website_sale_slides'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
