{
    'name': 'Loans Management',
    'description': """
Loans management
=================
Keeps track of loans, and creates corresponding journal entries.
    """,
    'category': 'Accounting/Accounting',
    'sequence': 32,
    'depends': ['account_asset', 'base_import'],
    'data': [
        'security/account_loans_security.xml',
        'security/ir.model.access.csv',

        'wizard/account_loan_close_wizard.xml',
        'wizard/account_loan_compute_wizard.xml',

        'views/account_asset_views.xml',
        'views/account_asset_group_views.xml',
        'views/account_loan_views.xml',
        'views/account_move_views.xml',
    ],
    'demo': [
        'demo/account_loans_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'post_init_hook': '_account_loans_post_init',
    'assets': {
        'web.assets_backend': [
            'account_loans/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'account_loans/static/tests/*',
        ],
    }
}
