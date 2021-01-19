# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Events Booths Sales",
    'category': 'Marketing/Events',
    'version': '1.0',
    'summary': "Manage event booths sale",
    'description': """
You can now sell your event booths
    """,
    'depends': ['event_booth', 'event_sale'],
    'data': [
        'security/ir.model.access.csv',

        'data/product_data.xml',

        'views/assets.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/event_booth_registration_views.xml',
        'views/event_booth_slot_views.xml',
        'views/event_booth_views.xml',

        'wizard/event_booth_configurator_views.xml',
        'wizard/event_booth_slot_editor_views.xml',
    ],
    'demo': [
        'data/event_booth_demo.xml',
    ],
    'auto_install': True
}
