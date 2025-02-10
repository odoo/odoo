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
        'l10n_dk_oioubl',
        'account_peppol',
    ],
    'auto_install': ['l10n_dk_oioubl'],
    'data': [
        'data/cron.xml',
        'data/oioubl_templates.xml',
        'security/ir.model.access.csv',
        'views/account_journal_dashboard_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/account_move_send_views.xml',
        'wizard/nemhandel_registration_views.xml',
    ],
    'demo': [
        'demo/l10n_dk_nemhandel_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_dk_nemhandel/static/src/components/**/*',
        ],
    },
    'license': 'LGPL-3',
}
