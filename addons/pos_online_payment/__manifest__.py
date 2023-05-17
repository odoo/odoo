# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Point of Sale online payment',
    'depends': ['point_of_sale', 'pos_restaurant', 'pos_self_order', 'account_payment'],
    'data': [
        'security/ir.model.access.csv',

        'views/payment_transaction_views.xml',
        'views/payment_portal_templates.xml',
        'views/account_payment_views.xml',
        'views/res_config_settings_views.xml',
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_online_payment/static/src/js/Popups/OnlinePaymentPopup.js',
            'pos_online_payment/static/src/js/Screens/PaymentScreen.js',
            'pos_online_payment/static/src/js/models.js',
            'pos_online_payment/static/src/xml/**/*',
            'pos_online_payment/static/src/css/popups/online_payment_popup.css',
        ],
    },
    'license': 'LGPL-3',
}
