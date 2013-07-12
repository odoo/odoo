{
    'name': 'E-Commerce',
    'category': 'Sale',
    'version': '1.0',
    'description': """
OpenERP E-Commerce
==================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'sale', 'point_of_sale'],
    'data': [
        'views/ecommerce.xml',
        'views/pricelist.xml'
    ],
    'js': ['static/src/js/ecommerce.js'],
    'css': ['static/src/css/ecommerce.css'],
    'installable': True,
    'auto_install': True,
}
