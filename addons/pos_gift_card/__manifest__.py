# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Gift Card for point of sales module",
    'summary': "Use gift card in your sales orders",
    'description': """Integrate gift card mechanism in sales orders.""",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['gift_card', 'point_of_sale'],
    'auto_install': True,
    'data': [
        'data/gift_card_data.xml',
        'views/gift_card_views.xml',
        'views/res_config_settings_views.xml',
        'views/pos_config_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_gift_card/static/src/css/giftCard.css',
            'pos_gift_card/static/src/js/models.js',
            'pos_gift_card/static/src/js/GiftCardButton.js',
            'pos_gift_card/static/src/js/GiftCardPopup.js',
            'pos_gift_card/static/src/js/PaymentScreen.js',
        ],
        'web.assets_qweb': [
            'pos_gift_card/static/src/xml/**/*',
        ],
        'web.assets_tests': [
            'pos_gift_card/static/src/js/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
