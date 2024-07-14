# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS IoT Six',
    'version': '1.0',
    'category': 'Sales/Point Of Sale',
    'summary': 'Integrate your POS with a Six payment terminal through IoT',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['pos_iot'],
    'installable': True,
    'license': 'OEEL-1',
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_iot_six/static/src/js/models.js',
            'pos_iot_six/static/src/js/payment_six.js',
        ],
    }
}
