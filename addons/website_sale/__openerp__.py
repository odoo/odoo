{
    'name': 'eCommerce',
    'category': 'Website',
    'summary': 'Sell Your Products Online',
    'website': 'https://www.odoo.com/page/e-commerce',
    'version': '1.0',
    'description': """
OpenERP E-Commerce
==================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'sale', 'payment'],
    'data': [
        'data/data.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/payment.xml',
        'views/sale_order.xml',
        'security/ir.model.access.csv',
        'security/website_sale.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'application': True,
}
