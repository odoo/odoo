{
    'name': 'Financial Statements (Community)',
    'version': '20.0.1.10.7',
    'category': 'Accounting/Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.access.csv',
        'data/balance_sheet.xml',
        'data/profit_and_loss.xml',
        'views/menus.xml',
        'views/account_move_views.xml',
        'views/report_pdf.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_fs_report/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
