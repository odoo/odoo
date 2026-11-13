{
    'name': 'Slovenia - eSlog e-invoicing',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
e-invoicing for Slovenia (eSlog)
    """,
    'depends': [
        'l10n_si',
        'account_edi_ubl_cii',
        'account_peppol',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'installable': True,
    #'post_init_hook': 'post_init',
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'LGPL-3',
}
