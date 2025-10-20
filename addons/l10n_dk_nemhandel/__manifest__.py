{
    'name': "Denmark EDI - Nemhandel",
    'summary': "This module is used to send/receive documents with Nemhandel",
    'description': """
        - Send and receive documents via Nemhandel network in OIOUBL 2.1 format
    """,
    'category': 'Accounting/Localizations/EDI',
    'version': '1.0',
    'depends': [
        'account_edi_proxy_client',
        'account_edi_ubl_cii',
        'l10n_dk',
    ],
    'auto_install': [
        'account_edi_ubl_cii',
        'l10n_dk',
    ],
    'data': [
        'data/cron.xml',
        'data/nemhandel_onboarding_tour.xml',
        'security/ir.model.access.csv',
        'views/account_journal_dashboard_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/nemhandel_registration_views.xml',
    ],
    'demo': [
        'demo/l10n_dk_nemhandel_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_dk_nemhandel/static/src/components/**/*',
            'l10n_dk_nemhandel/static/src/tours/nemhandel_onboarding.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'pre_init_hook': '_pre_init_nemhandel',
    'uninstall_hook': 'uninstall_hook',
}
