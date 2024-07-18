{
    'name': "Korea - Accounting",
    'icon': '/account/static/description/l10n.png',
    'countries': ['kr'],
    'version': '1.0',
    'category': 'Localization',
    'description': """
Korean Accounting Module
========================
    * changes the address format to Korean format.
    """,
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/res_country_data.xml',
    ],
    'license': 'LGPL-3',
}
