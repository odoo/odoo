{
    'name': "France - E-reporting for POS",
    'category': 'Accounting/Localizations/Reporting',
    'summary': 'Flux 10 e-reporting for POS',
    'depends': ['l10n_fr_pdp', 'point_of_sale', 'pos_account_peppol'],
    'data': ['views/res_partner_views.xml'],
    'assets': {
        'point_of_sale._assets_pos': ['l10n_fr_pdp_pos/static/src/**/*'],
    },
    'auto_install': True,
    'license': 'LGPL-3',
    'author': 'Odoo SA',
}
