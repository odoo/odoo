{
    'name': 'Romania - E-Transport',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
E-Transport implementation for Romania
    """,
    'depends': ['stock_delivery', 'l10n_ro_edi'],
    'assets': {
        'web.assets_backend': [
            'l10n_ro_edi_stock/static/src/components/**/*',
        ],
    },
    'data': [
        'data/template_etransport.xml',

        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
        'views/delivery_carrier_views.xml',

        'report/report_deliveryslip.xml',
    ],
    'installable': True,
    'license': "LGPL-3",
}
