# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'On site Payment & Picking',
    'version': '1.0',
    'category': 'Website/Website',
    'description': """
Allows customers to pay for their orders at a shop, instead of paying online.
""",
    'depends': ['website_sale', 'stock', 'payment_custom'],
    'data': [
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',  # Depends on `payment_method_pay_on_site`.
        'data/website_sale_picking_data.xml',

        'views/stock_warehouse_views.xml',
        'views/delivery_form_templates.xml',
        'views/delivery_view.xml',
        'views/res_config_settings_views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'assets': {
            'web.assets_frontend': [
                'website_sale_picking/static/src/js/location_selector/**/*'
            ]
    },
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
