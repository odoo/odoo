{
    'name': 'Türkiye - Nilvera',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
Base module containing core functionalities required by other Nilvera modules.
    """,
    'depends': ['l10n_tr'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'license': 'LGPL-3',
}
