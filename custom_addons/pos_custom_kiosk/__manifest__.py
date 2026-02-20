{
    'name': 'POS Custom Kiosk',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'author': 'Laxya',
    'summary': 'UX Tweaks for Native POS Self-Order',
    'description': """
        Customizations for the Self-Order UI.
        - Back to Website button.
        - Custom headers/branding tweaks.
    """,
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale.assets': [
            'pos_custom_kiosk/static/src/js/kiosk_tweaks.js',
            'pos_custom_kiosk/static/src/xml/kiosk_tweaks.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
