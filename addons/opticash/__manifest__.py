{
    'name': 'Opticash',
    'author': 'Optesis',
    'version': '1.7.0',
    'category': 'accounting',
    'description': """
    permet de faire la gestion de la caisse de dépense
""",
    'summary': 'Dépense de Caisse',
    'sequence': 9,
    'depends': ['base', 'account', 'l10n_pcgo'],
    'data': [
        'data/account_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/multi_company_view.xml',
        'views/optesis_cash_view.xml',
        'views/account_payment_view.xml',
        'views/menu_view.xml',
     ],
    'test': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
