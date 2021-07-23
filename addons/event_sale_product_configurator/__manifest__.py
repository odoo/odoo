# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Event Sale Product Configurator",
    'version': '1.0',
    'category': 'Hidden',
    'summary': "Bridge module between event_sale and sale_product_configurator",

    'description': """
        Technical bridge module installed to make the event_configurator work on the product_template_id field
        added by the product configurator.
    """,

    'depends': ['sale_product_configurator', 'event_sale'],
    'data': [
        'views/assets.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
