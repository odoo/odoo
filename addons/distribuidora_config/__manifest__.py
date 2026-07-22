{
    'name': "Distribuidora - Configuracion",
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Renombrar y ocultar menus nativos para esta empresa",
    'author': "Distribuidora",
    'depends': ['contacts', 'sale_management', 'point_of_sale', 'crm'],
    'data': [
        'data/menu_overrides.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
