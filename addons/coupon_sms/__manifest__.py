# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Coupon - SMS",
    'summary': 'Add SMS capabilities to Coupon',
    'description': 'Add SMS capabilities to Coupon',
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['coupon', 'sms'],
    'data': [
        'data/sms_data.xml',
        'views/coupon_views.xml',
    ],
    'application': False,
    'auto_install': True,
}
