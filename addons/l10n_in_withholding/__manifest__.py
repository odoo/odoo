{
    'name': 'Indian - TDS and TCS',
    'version': '1.0',
    'countries': ['in'],
    'description': """
        Support for Indian TDS (Tax Deducted at Source).
    """,
    'category': 'Accounting/Localizations',
    'depends': ['l10n_in'],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_in.section.alert.csv',
        'data/account_tax_report_tcs_data.xml',
        'data/account_tax_report_tds_data.xml',
        'wizard/l10n_in_withhold_wizard.xml',
        'views/l10n_in_section_alert_views.xml',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'views/account_move_line_views.xml',
        'views/account_payment_views.xml',
        'views/account_tax_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'post_init_hook': '_l10n_in_withholding_post_init',
    'license': 'LGPL-3',
}
