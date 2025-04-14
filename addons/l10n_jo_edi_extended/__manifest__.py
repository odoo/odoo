{
    'name': 'Jordan E-Invoicing Extended Features',
    'countries': ['jo'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Extended features for JoFotara',
    'description': """
This module improves the Jordan E-invoicing (JoFotara) by the following:
       1. Adds support for different invoice types and payment methods.
       2. Introduces demo mode.
    """,
    'depends': ['l10n_jo_edi'],
    'data': [
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
