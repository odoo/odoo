# -*- coding: utf-8 -*-
{
    'name': 'Digital Signatures',
    'version': '1.0',
    'category': 'Website',
    'description': """
Sign and complete your documents easily. Customize your documents with text and signature fields and send them to your recipients.\n
Let your customers follow the signature process easily.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['knowledge', 'website'],
    'data': [
        'security/ir.model.access.csv',

        'views/signature_request_templates.xml',
        'views/signature_item_templates.xml',

        'views/signature_request_view.xml',
        'views/signature_item_view.xml',

        'data/signature_request.xml',
        'data/signature_item.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [],
    'installable': True,
}
