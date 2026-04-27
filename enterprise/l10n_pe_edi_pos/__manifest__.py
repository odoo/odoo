{
    'name': 'Peruvian Localization for the Point of Sale',
    'version': '0.1',
    'countries': ['pe'],
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'l10n_pe_edi',
        'point_of_sale',
    ],
    'data': [
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': ['l10n_pe_edi_pos/static/src/**/*'],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
