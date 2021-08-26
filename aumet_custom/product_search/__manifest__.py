{
    'name': 'Product Search ',
    'description': 'Product Search by Specific Criteria Active Ingredient & barcode scanner &Vendor Name ',
    'author': 'Aumet - walaa khaled ',
    'depends': ['product', 'stock', 'point_of_sale', 'web','flexipharmacy'],
    'data': [
        'views/product_view.xml',
        'views/templates.xml',
    ],
    'qweb': [],
    'application': True,
    'installable': True,
}
