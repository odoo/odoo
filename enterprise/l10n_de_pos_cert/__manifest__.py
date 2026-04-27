# -*- coding: utf-8 -*-

{
    'name': "Germany - Certification for Point of Sale",
    'summary': "Germany TSS Regulation",

    'description': """
This module brings the technical requirement for the new Germany regulation with the Technical Security System by using a cloud-based solution with Fiskaly.

Install this if you are using the Point of Sale app in Germany.

""",

    'category': 'Accounting/Localizations/Point of Sale',
    'version': '0.1',

    'depends': ['l10n_de', 'point_of_sale', 'iap'],
    'installable': True,
    'auto_install': True,

    'data': [
        'security/ir.model.access.csv',
        'security/l10n_de_pos_cert_security.xml',
        'views/l10n_de_pos_dsfinvk_export_views.xml',
        'views/point_of_sale_dashboard.xml',
        'views/res_config_settings_views.xml',
        'views/pos_order_views.xml',
        'views/res_company_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_de_pos_cert/static/src/**/*',
        ],
    },
    'license': 'OEEL-1',
}
