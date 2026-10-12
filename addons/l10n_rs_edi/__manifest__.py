{
    'author': 'Odoo S.A.',
    'name': 'Serbia - eFaktura E-invoicing',
    'category': 'Accounting/Localizations/EDI',
    'description': """
eFaktura E-invoice implementation for Serbia
    """,
    'summary': "E-Invoice implementation for Serbia",
    'countries': ['rs'],
    'depends': [
        'account_edi_ubl_cii',
        'l10n_rs',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/account_move.xml',
        'views/res_partner_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
