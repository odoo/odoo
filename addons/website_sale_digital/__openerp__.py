# -*- encoding: utf-8 -*-
{
    'name': 'Website Sale Digital - Sell digital products',
    'version': '0.1',
    'description': """
Sell digital product using attachments to virtual products
""",
    'depends': [
        'document',
        'website_sale',
    ],
    'installable': True,
    'data': [
        'views/product_views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
}
