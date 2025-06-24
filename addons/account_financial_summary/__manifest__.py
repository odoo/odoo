{
    'name': 'Financial Summary Reports',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Quick summary for ledger and balance reports',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/financial_summary_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
