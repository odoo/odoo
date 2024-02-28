# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'On site Payment & Picking',
    'version': '1.0',
    'category': 'Website/Website',
    'description': """
Allows customers to pay for their orders at a shop, instead of paying online.
""",
    'depends': ['website_sale_delivery', 'payment_custom'],
    'data': [
        'data/website_sale_picking_data.xml',
        'views/res_config_settings_views.xml',
        'views/templates.xml',
        'views/delivery_view.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_picking/static/src/js/checkout_form.js'
        ],
        'web.assets_tests': [
            'website_sale_picking/static/tests/tours/**/*.js'
        ]
    },
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
