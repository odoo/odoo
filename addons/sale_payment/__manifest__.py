# -*- coding: utf-8 -*-

{
    'name': 'Payment - Sale',
    'category': 'Sales',
    'summary': 'Link Sales and Payment',
    'version': '1.0',
    'description': """Link Sales and Payment

Provide tools for sale-related payment

 * specific management of transactions like sale order confirmation
 * tools method to handle transactions when allowing to pay / sell
 * JS code to handle a payment form (eCommerce
 * add payment-related fields on SO
""",
    'depends': ['payment', 'sale'],
    'data': [
        'views/sale_portal_templates.xml',
        'views/settings.xml',
        'views/payment_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
