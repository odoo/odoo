{
    'name': 'France - PDP Invoice Compliance',
    'category': 'Accounting/Localizations/EDI',
    'description': """
Adds the mandatory late payment penalty information to French invoices.
""",
    'depends': [
        'l10n_fr_pdp',
    ],
    'auto_install': ['l10n_fr_pdp'],
    'data': [
        'views/account_invoice_report_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}
