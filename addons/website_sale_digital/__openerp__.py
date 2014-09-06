{
    'name': 'Website Sale Digital - Sell digital products',
    'version': '0.0.1',
    'description': """
Sell digital product using attachments to virtual products
""",
    'author': 'OpenERP S.A.',
    'depends': [
        'document',
        'website_sale',
    ],
    'installable': True,
    'data': [
        'views/website_sale_digital.xml',
    ],
    'demo': [
    ],
    'qweb': [
    ],
}
