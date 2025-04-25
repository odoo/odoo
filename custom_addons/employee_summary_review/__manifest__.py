{
    'name': 'Employee Daily Summary & Review',
    'version': '1.0',
    'summary': 'Submit and review daily work summaries',
    'license': 'LGPL-3',
    'category': 'Human Resources',
    'author': 'Your Name',
    'depends': ['base', 'hr', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/daily_summary_views.xml',
        'views/summary_review_views.xml',
    ],
    'installable': True,
    'application': True,
}
