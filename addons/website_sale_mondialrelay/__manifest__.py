# -*- coding: utf-8 -*-
{
    'name': "eCommerce Mondialrelay Delivery",
    'summary': "Let's choose Point Relais® on your ecommerce",

    'description': """
This module allow your customer to choose a Point Relais® and use it as shipping address.
    """,
    'category': 'Website/Website',
    'version': '0.1',
    'depends': ['website_sale', 'delivery_mondialrelay'],
    'data': [
        'views/delivery_carrier_views.xml',
        'views/delivery_form_templates.xml',
        'views/res_config_settings_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_mondialrelay/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
    'auto_install': True,
}
