{
    'name': 'Electronic invoicing for POS in Colombia',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Colombian Localization for POS and EDI documents',
    'depends': ['l10n_co_pos', 'l10n_co_dian', 'pos_edi_ubl'],
    'data': [
        'views/account_journal_views.xml',
        'views/pos_payment_method_views.xml',
        'views/res_config_settings_views.xml',
        'views/pos_session_sales_details.xml',
        'views/pos_order_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_co_edi_pos/static/src/**/**',
        ],
        'web.assets_tests': [
            'l10n_co_edi_pos/static/tests/**/**',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
}
