{
    'name': 'France - PDP',
    'category': 'Accounting/Localizations/EDI',
    'website': "https://www.odoo.com/documentation/18.0/applications/finance/fiscal_localizations/france.html#PDP",
    'description': """TODO:
""",
    'depends': [
        'l10n_fr_account',
        'account_edi_proxy_client',
        'account_edi_ubl_cii',
    ],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'views/account_journal_dashboard_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'wizard/pdp_registration_views.xml',
    ],
    'demo': [
        'demo/l10n_fr_pdp_demo.xml',
    ],
    'license': 'LGPL-3',
    'pre_init_hook': '_pre_init_pdp',
    'uninstall_hook': 'uninstall_hook',
}
