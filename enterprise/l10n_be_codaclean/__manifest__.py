{
    'name': 'Codaclean',
    'version': '1.0',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/belgium.html#codaclean',
    'category': 'Accounting/Localizations',
    'description': 'Connect to Codaclean and automatically import CODA statements.',
    'depends': [
        'l10n_be_coda',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/account_journal_dashboard_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/connection_wizard.xml',
    ],
    'license': 'OEEL-1',
}
