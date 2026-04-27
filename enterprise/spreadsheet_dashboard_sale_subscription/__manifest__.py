# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for subscriptions",
    'category': 'Hidden',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'sale_subscription'],
    'data': [
        "data/dashboards.xml",
        "views/sale_subscription_report_views.xml",
    ],
    'installable': True,
    'auto_install': ['sale_subscription'],
    'license': 'OEEL-1',
}
