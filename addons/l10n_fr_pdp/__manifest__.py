{
    'name': 'France - E-Invoicing (Approved Platform)',
    'category': 'Accounting/Localizations/EDI',
    'website': "https://www.odoo.com/documentation/18.0/applications/finance/fiscal_localizations/france.html#PDP",
    'description': """
        - Support for the mandatory electronic invoicing in France
        - Send and receive documents via the Odoo approved platform
""",
    'depends': [
        'l10n_fr_account',
        'account_peppol',
        'iap',
    ],
    'auto_install': ['l10n_fr_account'],
    'data': [
        'data/ir_cron.xml',
        'views/account_journal_dashboard_views.xml',
        'views/account_move_views.xml',
        'views/account_peppol_response_views.xml',
        'views/l10n_fr_account_inherit.xml',
        'views/pdp_flow_views.xml',
        'views/pdp_send_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'wizard/pdp_config_wizard.xml',
        'wizard/pdp_registration_views.xml',
        'wizard/pdp_response_wizard_views.xml',
        'wizard/l10n_fr_pdp_partner_lookup.xml',
        'security/ir.access.csv',
    ],
    'author': 'Odoo S.A.',
    'assets': {
        'web.assets_backend': [
            'l10n_fr_pdp/static/src/js/**',
        ],
    },
    'license': 'LGPL-3',
    'pre_init_hook': '_pre_init_pdp',
    'post_init_hook': '_post_init_pdp',
    'uninstall_hook': 'uninstall_hook',
}
