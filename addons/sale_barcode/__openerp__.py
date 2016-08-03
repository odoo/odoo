# -*- coding: utf-8 -*-

{
    'name': "Sale Barcode Scanning",
    'summary': "Add barcode scanning facilities to Sale Management.",
    'description': """
        Allows to scan product barcodes in Sale Management forms.
    """,
    'author': "Odoo SA",
    'category': 'Usability',
    'version': '1.0',
    'depends': ['barcodes', 'sale'],
    'data': [
        'views/inherited_sale_order_views.xml',
    ],
    'auto_install': True,
}
