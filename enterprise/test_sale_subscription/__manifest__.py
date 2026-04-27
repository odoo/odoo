# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Sale Subscription',
    'version': '1.0',
    'depends': ['sale_subscription'],
    'website': 'https://www.odoo.com/app/accounting',
    'category': 'Sales/Subscriptions',
    'demo': ['data/sale_subscription_demo.xml'],
    'installable': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_tests': [
            'test_sale_subscription/static/tests/tours/*',
        ],
    },
}
