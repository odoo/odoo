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
        'views/res_config_settings_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_mondialrelay/static/src/js/website_sale_mondialrelay.js',
            'website_sale_mondialrelay/static/src/xml/website_sale_mondialrelay.xml',
        ],
    },
    'license': 'LGPL-3',
    'auto_install': True,
}
