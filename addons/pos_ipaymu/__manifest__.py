# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'IPaymu Payment Services',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Ipaymu TAG QR Code Payment for Point Of Sale',
    'description': """
Allow Ipaymu TAG QR Code Payment for Point Of Sale
**************************************************

This module allows customers to pay for their orders with IPaymu
TAG Mobile QR Payment. The transactions are processed by IPaymu.com
PT Inti Prima Mandiri Utama). IPaymu merchant account is necessary.

Usage:
* It allows Fast payment by scan QR Code on the payment screen.

IPaymu.com is a payment gateway in Indonesia, only IDR is supported.
Please sign up your account at https://www.ipaymu.com
    """,
    'depends': ['web', 'point_of_sale'],
    'website': 'https://www.ipaymu.com',
    'data': [
        'security/ir.model.access.csv',
        'views/pos_ipaymu_templates.xml',
        'views/pos_ipaymu_views.xml',
        'views/pos_config_setting_views.xml',
    ],
    'qweb': [
        'static/src/xml/pos_ipaymu.xml',
    ],
}
