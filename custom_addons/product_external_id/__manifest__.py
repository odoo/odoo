{
    'name': 'Product External ID Display',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Display External ID on products',
    'description': """
        This module adds the ability to see the External ID directly on product forms.
        External IDs are useful for integration with third-party systems.
    """,
    'depends': ['product'],
    'data': [
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 