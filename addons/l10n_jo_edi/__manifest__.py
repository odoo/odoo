{
    'name': 'Jordan E-Invoicing',
    'countries': ['jo'],
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Electronic Invoicing for Jordan UBL 2.1',
    'author': 'Odoo S.A., Smart Way Business Solutions',
    'description': """
       Allows the users to integrate with JoFotara.
    """,
    'depends': ['account_edi_ubl_cii', 'l10n_jo'],
    'data': [
        'views/account_move_views.xml',
        'views/report_invoice.xml',
        'views/report_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'auto_install': ['l10n_jo'],
    'assets': {
        'web.assets_backend': [
            'l10n_jo_edi/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
    'post_init_hook': '_post_init_hook',
}
