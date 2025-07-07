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
        'data/uom_data.xml',
        'security/ir.access.csv',
    ],
    'post_init_hook': '_l10n_tr_nilvera_post_init',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
