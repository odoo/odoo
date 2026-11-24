{
    'name': 'Financial Statements (Community)',
    'version': '20.0.1.9.6',
    'category': 'Accounting/Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.access.csv',
        'views/menus.xml',
        'data/balance_sheet.xml',
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
