{
    'name': 'Jordan E-Invoicing Extended Features',
    'countries': ['jo'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Extended Features for Jordan Electronic Invoicing',
    'author': 'Odoo S.A., Smart Way Business Solutions',
    'description': """
       Allows the users to change the invoice trade type and payment method.
    """,
    'depends': ['l10n_jo_edi'],
    'data': [
        'views/account_move_views.xml',
        'views/account_payment_term_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
