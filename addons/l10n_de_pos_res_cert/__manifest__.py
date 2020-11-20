# -*- coding: utf-8 -*-

{
    'name': "l10n_de_pos_res_cert",

    'summary': """
        Germany TSS Regulation for restaurant
    """,

    'description': """
    """,

    'category': 'Accounting/Localizations/Point of Sale',
    'version': '0.1',

    'depends': ['pos_restaurant', 'l10n_de_pos_cert'],
    'installable': True,
    'auto_install': True,
    'application': False,

    'data': [
        'views/l10n_de_pos_res_cert_templates.xml',
    ],
}
