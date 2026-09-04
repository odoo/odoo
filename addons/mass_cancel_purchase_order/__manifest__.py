# -*- coding: utf-8 -*-
{
    'name': 'Mass Cancel Purchase Order',
    'summary': "Mass Cancel Purchase Order",
    'description': "Mass Cancel Purchase Order",

    'author': 'iPredict IT Solutions Pvt. Ltd.',
    'website': 'http://ipredictitsolutions.com',
    'support': 'ipredictitsolutions@gmail.com',

    'category': 'Purchases',
    'version': '16.0.0.1.0',
    'depends': ['purchase'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_order_cancel.xml',
    ],

    'license': "OPL-1",
    'auto_install': False,
    'installable': True,

    'images': ['static/description/banner.png'],
    'pre_init_hook': 'pre_init_check',
}
