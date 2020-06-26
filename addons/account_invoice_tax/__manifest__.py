{
    'name': 'Account Invoice Tax',
    'version': "1.0",
    'description': """Add new buttons in the Vendor Bills that let us to add/remove taxes to all the lines
of a vendor bill.""",
    'author': 'ADHOC SA',
    'category': 'Localization',
    'depends': [
        'account',
    ],
    'data': [
        'wizards/account_invoice_tax_view.xml',
        'views/account_move_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
