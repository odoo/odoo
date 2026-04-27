{
    'name': 'Estonia - Rounding',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'version': '1.0',
    'icon': '/account/static/description/l10n.png',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This bridge module adds the necessary fields to properly round the Tax Report for Estonia in the closing entries.
    """,
    'author': 'Odoo SA',
    'depends': ['l10n_ee_reports'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'post_init_hook': '_l10n_ee_rounding_post_init',
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
}
