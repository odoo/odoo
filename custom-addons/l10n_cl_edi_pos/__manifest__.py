# -*- coding: utf-8 -*-

{
    'name': "Chilean module for Point of Sale",

    'summary': "Chilean module for Point of Sale",

    'description': """
This module brings the technical requirement for the Chilean regulation.
Install this if you are using the Point of Sale app in Chile.    

""",

    'category': 'Accounting/Localizations/Point of Sale',
    'version': '1.0',

    'depends': ['l10n_cl_edi', 'point_of_sale'],
    'installable': True,
    'auto_install': True,
    'data': [
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_cl_edi_pos/static/src/**/*'
        ],
    },
    'license': 'OEEL-1',
}
