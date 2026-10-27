{
    'author': 'Odoo',
    'name': 'Serbia - eFaktura E-invoicing',
    'version': '1.0',
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
        'wizard/account_move_send_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
