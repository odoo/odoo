{
    'name': 'E-Commerce',
    'category': 'Website',
    'summary': 'Sell Your Products Online',
    'version': '1.0',
    'description': """
OpenERP E-Commerce
==================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'sale', 'product', 'payment_acquirer'],
    'data': [
        'website_sale_data.xml',
        'views/website_sale.xml',
        'views/website_sale_backend.xml',
        'security/ir.model.access.csv',
        'security/website_sale.xml',
    ],
    'demo': [
        'website_sale_demo.xml',
        'demo/website_sale_homepage_demo.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
