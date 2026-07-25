{
    'name': 'Invoice Agent',
    'version': '19.0.0.2.0',
    'category': 'Accounting/Accounting',
    'summary': 'AI Extraction capabilities for account.move — computed fields, vendor matching, journal config',
    'depends': ['account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'views/account_journal_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
