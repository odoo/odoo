# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'UPS: Bill My Account',
    'category': 'Inventory/Delivery',
    'summary': 'Bill to your UPS account number',
    'description': """
This module allows ecommerce users to enter their UPS account number and delivery fees will be charged on that account number.
    """,
    'depends': ['delivery_ups', 'website_sale', 'payment_custom'],
    'data': [
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',  # Depends on `payment_method_cash_on_delivery`.

        'views/delivery_ups_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'website_sale_ups/static/src/js/delivery_ups.js',
        ],
        'web.assets_frontend': [
            'website_sale_ups/static/src/**/*',
        ],
    }
}
