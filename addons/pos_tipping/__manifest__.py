# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'POS Tipping',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': 'Allows for American-style tipping in the POS',
    'description': """
This module allows someone to capture the total and some configurable tip

""",
    'depends': ['pos_restaurant'],
    'website': 'https://www.odoo.com/page/point-of-sale-restaurant',
    'data': [
        'views/pos_order_views.xml',
        'views/pos_payment_views.xml',
        'views/pos_config_views.xml',
        'views/pos_tipping_templates.xml',
    ],
    'qweb': [
        'static/src/xml/tipping.xml',
    ],
    'installable': True,
    'auto_install': False,
}
