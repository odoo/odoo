{
    'name': 'Invoice Agent',
    'version': '19.0.0.1.0',
    'category': 'Accounting/Accounting',
    'summary': 'AI Extraction capabilities for account.move',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
