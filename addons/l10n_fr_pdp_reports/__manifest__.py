{
    'name': "France - PDP E-reporting",
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'summary': 'PDP Flux 10 e-reporting flow for France',
    'depends': ['l10n_fr_pdp', 'account_edi_ubl_cii_tax_extension'],
    'data': [
        'security/ir.model.access.csv',
        'data/pdp_cron.xml',
        'views/l10n_fr_account_inherit.xml',
        'views/account_move_views.xml',
        'views/pdp_flow_views.xml',
        'views/pdp_send_wizard_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
