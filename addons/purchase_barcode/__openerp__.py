# -*- coding: utf-8 -*-

{
    'name': "Purchase Barcode Scanning",
    'summary': "Add barcode scanning facilities to Purchase Management.",
    'description': """
        Allows to scan product barcodes in Purchase Management forms.
    """,
    'author': "Odoo SA",
    'category': 'Usability',
    'version': '1.0',
    'depends': ['barcodes', 'purchase'],
    'data': [
        'views/inherited_purchase_order_views.xml',
    ],
    'auto_install': True,
}
