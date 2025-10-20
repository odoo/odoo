{
    'author': 'Odoo S.A.',
    'name': 'Romania - E-invoicing',
    'category': 'Accounting/Localizations/EDI',
    'description': """
E-invoice implementation for Romania
    """,
    'summary': "E-Invoice implementation for Romania",
    'depends': [
        'account_edi_ubl_cii',
        'l10n_ro',
    ],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'l10n_ro_edi/static/src/components/*',
        ],
    }
}
