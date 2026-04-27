# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sale Commission: Subscription',
    'version': '1.0',
    'category': 'Sales/Commission',
    'sequence': 105,
    'summary': "Manage your salespersons' commissions",
    'description': """
    """,
    'depends': ['sale_commission', 'sale_subscription'],
    'data': [
        'views/sale_commission_plan_view.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
