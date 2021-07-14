{
    'name': 'Manual Checks Management',
    'version': "1.0.0",
    'category': 'Accounting',
    'summary': 'Manual Checks Management',
    'description': """
This module extends 'Check Printing Base' module to:
* allow using own checks that are not printed but filled manually by the user
* allow to use checkbooks to track numbering
* add an optional "payment date" for postdated checks
* add a menu to track own checks
""",
    'author': 'ADHOC SA',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'account_check_printing',
    ],
    'data': [
        'views/account_payment_view.xml',
        'views/account_checkbook_view.xml',
        'views/account_journal_view.xml',
        'security/ir.model.access.csv',
        'wizards/account_payment_register_views.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
