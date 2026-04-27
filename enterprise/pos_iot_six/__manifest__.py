# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS IoT Six',
    'version': '1.0',
    'category': 'Sales/Point Of Sale',
    'summary': 'Integrate your POS with a Six payment terminal through IoT',
    'data': [
        'wizard/add_six_terminal_views.xml',
        'views/pos_payment_method_views.xml',
        'views/iot_box_views.xml',
        'security/ir.model.access.csv'
    ],
    'depends': ['pos_iot'],
    'installable': True,
    'license': 'OEEL-1',
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_iot_six/static/src/js/balance_button.js',
            'pos_iot_six/static/src/js/models.js',
            'pos_iot_six/static/src/js/payment_six.js',
            'pos_iot_six/static/src/xml/balance_button.xml',
        ],
        'web.assets_backend': [
            'pos_iot_six/static/src/js/six_terminal_id_field.*',
            'pos_iot_six/static/src/css/six_terminal_id_field.css',
        ],
    }
}
