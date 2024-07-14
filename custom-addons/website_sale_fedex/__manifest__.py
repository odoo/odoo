# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'FEDEX Locations for Website Delivery',
    'category': 'Inventory/Delivery',
    'summary': 'Allows website customers to choose delivery pick-up points',
    'description': 'This module allows ecommerce users to choose to deliver to Pick-Up points for the FEDEX connector.',
    'depends': ['delivery_fedex', 'website_sale'],
    'data': [
        'views/delivery_fedex_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_fedex/static/src/xml/fedex_pickup_locations.xml',
        ],
    },

    'auto_install': True,
    'license': 'OEEL-1',
}
