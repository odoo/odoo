{
    'name': 'Website Sale Combo Suggestions',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Suggest combo packs during checkout when individual products are in cart',
    'description': """
        This module automatically detects when users have individual products in their cart
        that could be replaced by a cheaper combo pack and suggests the substitution.
    """,
    'depends': ['website_sale'],
    'assets': {
        'web.assets_frontend': [
            'website_sale_combo_suggestions/static/src/js/combo_manager.js',
        ],
    },
    'installable': True,
    'author': 'Diogo Rodrigues, Beatriz Abreu',
    'license': 'LGPL-3',
}
