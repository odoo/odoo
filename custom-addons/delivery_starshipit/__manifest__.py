# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Starshipit Shipping",
    'description': """
Send your shippings through Starshipit and track them online
=======================================================

Starshipit is the leading provider of integrated shipping and tracking solutions for growing e-commerce businesses.
Seamlessly integrating with a large range of couriers and platforms,
you can streamline every step of your fulfilment process,
reduce handling time and improve customer experience.
    """,
    'category': 'Inventory/Delivery',
    'version': '1.0',
    'application': True,
    'depends': ['stock_delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_carrier_views.xml',
        'wizard/starshipit_shipping_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'delivery_starshipit/static/src/components/**/*.js',
            'delivery_starshipit/static/src/components/**/*.xml',
        ],
    },
    'license': 'OEEL-1',
}
