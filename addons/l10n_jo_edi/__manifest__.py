{
    'name': 'Jordan E-Invoicing',
    'countries': ['jo'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Electronic Invoicing for Jordan UBL 2.1',
    'author': 'Odoo S.A., Smart Way Business Solutions',
    'description': """
       Allows the users to integrate with JoFotara.
    """,
    'depends': ['account_edi_ubl_cii', 'l10n_jo'],
    'data': [
        'data/ubl_jo_templates.xml',
        'views/account_move_views.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_jo'],
    'license': 'LGPL-3',
    'post_init_hook': '_post_init_hook',
}
