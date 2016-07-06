# -*- coding: utf-8 -*-

{
    'name': 'COD Payment Acquirer',
    'category': 'Hidden',
    'summary': 'COD(Collect on Delivery/Cash on Delivery)',
    'version': '1.0',
    'description': """COD Payment Acquirer""",
    'depends': ['website_sale_delivery'],
    'data': [
        'views/cod.xml',
        'data/payment_cod_data.xml',
    ],
    'installable': True,
    'auto_install': True,
}
