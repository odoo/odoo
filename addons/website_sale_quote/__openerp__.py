{
    'name': 'Quote Roller',
    'category': 'Website',
    'summary': 'Send Live Quotation',
    'version': '1.0',
    'description': """
OpenERP Sale Quote Roller
==================

        """,
    'author': 'OpenERP SA',
    'depends': ['website_sale','portal_sale', 'mail'],
    'data': [
        'views/website_sale_quote.xml',
        'sale_quote_view.xml',
        'sale_quote_data.xml'
    ],
    'demo': [
        'sale_quote_demo.xml'
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
