{
    'name': 'eCommerce Delivery Methods',
    'category': 'Website',
    'summary': 'Add delivery costs to sales',
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
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
}
