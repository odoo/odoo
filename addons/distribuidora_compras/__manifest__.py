{
    'name': "Distribuidora - Compras",
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': "Consolidacion de compra para CENADA y proveedores cercanos",
    'author': "Distribuidora",
    'depends': ['sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/compra_consolidada_wizard_views.xml',
        'report/compra_consolidada_report.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
