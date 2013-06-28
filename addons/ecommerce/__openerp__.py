{
    'name': 'E-Commerce',
    'category': 'Sale',
    'version': '1.0',
    'description': """
OpenERP E-Commerce
==================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'sale_stock', 'point_of_sale'],
    'installable': True,
    'data': [
        'views/ecommerce.xml'
    ],
}
