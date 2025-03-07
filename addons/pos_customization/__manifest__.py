{
    'name': 'POS Customization',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Customizations for Odoo Point of Sale',
    'description': """
        This module extends the Odoo POS with custom features, starting with a POS-specific description field for products.
    """,
    'depends': ['point_of_sale'],
    'data': [
        'views/product_view.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_customization/static/src/**/*',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
