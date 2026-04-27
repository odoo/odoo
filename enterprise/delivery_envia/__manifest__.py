# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Envia Shipping",
    'description': """
Send your shippings through Envia and track them online
=======================================================

Envia is a provider of integrated shipping and tracking solutions for growing e-commerce businesses.
Seamlessly integrating with a large range of couriers and platforms,
you can streamline every step of your fulfilment process,
reduce handling time and improve customer experience.
    """,
    'category': 'Inventory/Delivery',
    'version': '1.0',
    'application': True,
    'depends': ['stock_delivery', 'base_address_extended', 'phone_validation'],
    'data': [
        'security/ir.model.access.csv',
        'data/delivery_envia.xml',
        'views/delivery_carrier_views.xml',
        'wizard/envia_shipping_wizard.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'delivery_envia/static/src/components/**/*.js',
            'delivery_envia/static/src/components/**/*.xml',
        ],
    },
    'license': 'OEEL-1',
}
