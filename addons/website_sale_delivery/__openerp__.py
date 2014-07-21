{
    'name': 'eCommerce Delivery',
    'category': 'Website',
    'summary': 'Add Delivery Costs to Online Sales',
    'version': '1.0',
    'description': """
Delivery Costs
==============
""",
    'author': 'OpenERP SA',
    'depends': ['website_sale', 'delivery'],
    'data': [
        'views/website_sale_delivery.xml',
        'views/website_sale_delivery_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
}
