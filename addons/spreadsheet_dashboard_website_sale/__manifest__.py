# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for eCommerce",
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'website_sale'],
    'data': [
        'data/dashboards.xml',
    ],
    'auto_install': ['website_sale'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
