# -*- coding: utf-8 -*-
{
    'name': "Consolidation",
    'category': 'Accounting/Accounting',
    'sequence': 205,
    'summary': """All you need to make financial consolidation""",
    'description': """All you need to make financial consolidation""",
    'depends': ['account_reports','web_grid'],
    'data': [
        'security/account_consolidation_security.xml',
        'security/ir.model.access.csv',
        'data/consolidated_balance_report.xml',
        'data/account_report_actions.xml',
        'data/onboarding_data.xml',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'views/consolidation_account_views.xml',
        'views/consolidation_journal_views.xml',
        'views/consolidation_period_views.xml',
        'views/consolidation_account_group_views.xml',
        'views/consolidation_chart_views.xml',
        'views/consolidation_rate_views.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'account_consolidation/static/src/scss/consolidation_kanban.scss',
            'account_consolidation/static/src/components/**/*',
            'account_consolidation/static/src/views/**/*',
        ],
        'web.qunit_suite_tests': [
            'account_consolidation/static/tests/**/*',
        ]
    },
    'license': 'OEEL-1',
}
