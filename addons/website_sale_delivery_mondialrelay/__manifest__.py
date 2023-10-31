# -*- coding: utf-8 -*-
{
    'name': "website_sale_delivery_mondialrelay",
    'summary': """ Let's choose Point Relais® on your ecommerce """,

    'description': """
        This module allow your customer to choose a Point Relais® and use it as shipping address.
    """,
    'category': 'Website/Website',
    'version': '0.1',
    'depends': ['website_sale_delivery', 'delivery_mondialrelay'],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_delivery_mondialrelay/static/src/js/website_sale_delivery_mondialrelay.js',
        ],
    },
    'license': 'LGPL-3',
    'auto_install': True,
}
