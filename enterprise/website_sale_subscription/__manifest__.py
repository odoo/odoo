# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'eCommerce Subscription',
    'category': 'Hidden',
    'summary': 'Sell subscription products on your eCommerce',
    'version': '1.0',
    'description': """
This module allows you to sell subscription products in your eCommerce with
appropriate views and selling choices.
    """,
    'depends': ['website_sale', 'sale_subscription'],
    'data': [
        'views/templates.xml',
        'views/sale_order_views.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sale_subscription/static/src/js/combo_configurator_dialog/*',
            'sale_subscription/static/src/js/product_configurator_dialog/*',
            ('before', 'website_sale/static/src/js/website_sale.js', 'website_sale_subscription/static/src/js/variant_mixin.js'),
            'website_sale_subscription/static/src/js/website_sale_subscription.js',
            'website_sale_subscription/static/src/js/website_sale_configurators.js',
            'website_sale_subscription/static/src/xml/pricing_view.xml',
        ],
        'web.assets_tests': [
            'website_sale_subscription/static/tests/tours/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
