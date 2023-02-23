# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Events Booths Sales",
    'category': 'Marketing/Events',
    'version': '1.1',
    'summary': "Manage event booths sale",
    'description': """
Sell your event booths and track payments on sale orders.
    """,
    'depends': ['event_booth', 'event_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'data/event_booth_category_data.xml',
        'views/sale_order_views.xml',
        'views/event_type_booth_views.xml',
        'views/event_booth_category_views.xml',
        'views/event_booth_registration_views.xml',
        'views/event_booth_views.xml',
        'wizard/event_booth_configurator_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'event_booth_sale/static/src/**/*',
        ]
    },
    'license': 'LGPL-3',
}
