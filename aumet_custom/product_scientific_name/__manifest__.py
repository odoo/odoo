{
    'name': 'Product Scientific Name',
    'description': 'Product Scientific Name & Search ',
    'category': 'Inventory/Product',
    'sequence': 1,
    'version': '1.0.2',
    'author': 'walaa khaled ',
    'depends': ['product', 'stock', 'point_of_sale', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_scientific_name_view.xml',
        'views/product_view.xml',
        'views/templates.xml',
    ],
    'qweb': [],
    'application': True,
    'installable': True,
}
