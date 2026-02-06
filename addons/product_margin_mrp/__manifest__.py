{
    'name': 'Adds MRP cost to Product Margin Report ',
    'description': """
    Adds MRP cost to Product's Margin Report
""",
    'depends': ['account', 'mrp', 'product_margin'],
    'data': [
        'views/product_product_views.xml'
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
