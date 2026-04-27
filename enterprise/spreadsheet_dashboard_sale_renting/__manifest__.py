# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for rental",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'sale_renting'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['sale_renting'],
    'license': 'OEEL-1',
}
