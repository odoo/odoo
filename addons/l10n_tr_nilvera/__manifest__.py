{
    'name': 'Türkiye - Nilvera',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
Base module containing core functionalities required by other Nilvera modules.
    """,
    'depends': ['l10n_tr'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'security/ir.access.csv',
    ],
    'license': 'LGPL-3',
}
