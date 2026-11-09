{
    'name': 'France - Octroi de Mer',
    'icon': '/account/static/description/l10n.png',
    'author': 'Odoo SA',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This module introduce the french Octroi de Mer, which is a specific case for Drom.
""",
    'depends': [
        'l10n_fr_account',
        'l10n_fr_pdp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/l10n_fr_octroi_de_mer_code.xml',
        'views/product_template_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
}
