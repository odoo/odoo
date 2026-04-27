# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for marketing automation",
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'marketing_automation'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['marketing_automation'],
    'license': 'LGPL-3',
}
