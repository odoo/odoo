{
    'author': 'Odoo',
    'name': 'Romania - E-invoicing',
    'version': '1.0',
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
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'l10n_ro_edi/static/src/components/*',
        ],
        'web.tests_assets': [
            'l10n_ro_edi/static/tests/legacy/helpers/mock_server.js',
        ],
    }
}
