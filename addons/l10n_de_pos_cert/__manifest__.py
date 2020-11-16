# -*- coding: utf-8 -*-

{
    'name': "l10n_de_pos_cert",

    'summary': """
        Germany TSS Regulation
    """,

    'description': """
        This module brings the technical requirement for the new Germany regulation with the Technical Security System by using a cloud-based solution with Fiskaly.
        
        Install this if you are using the Point of Sale app in Germany.    
        
    """,

    'category': 'Accounting/Localizations/Point of Sale',
    'version': '0.1',

    'depends': ['l10n_de', 'point_of_sale'],
    'installable': True,
    'auto_install': True,
    'application': False,

    'data': [
        'data/ir_config_param.xml',
        'views/l10n_de_pos_cert_templates.xml',
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
        'views/res_company_views.xml',
    ],
    'qweb': ['static/src/xml/OrderReceipt.xml'],
}
