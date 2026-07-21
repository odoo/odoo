{
    'name': "Distribuidora - Ventas",
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Captura de pedidos y precios por cliente para la distribuidora",
    'author': "Distribuidora",
    'depends': ['sale', 'account'],
    'data': [
        'data/res_partner_category_data.xml',
        'views/sale_order_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
