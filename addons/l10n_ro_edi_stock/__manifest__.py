{
    'name': 'Romania - E-Transport',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
E-Transport implementation for Romania
    """,
    'depends': ['stock_delivery', 'sale_management', 'account_intrastat', 'l10n_ro_efactura'],
    'assets': {
        'web.assets_backend': [
            'l10n_ro_edi_stock/static/src/components/**/*',
        ],
    },
    'data': [
        'security/ir.model.access.csv',

        'data/template_etransport.xml',

        'views/stock_picking_views.xml',
        'views/delivery_carrier_views.xml',

        'report/report_deliveryslip.xml',
    ],
    'installable': True,
    'license': "LGPL-3",
}
