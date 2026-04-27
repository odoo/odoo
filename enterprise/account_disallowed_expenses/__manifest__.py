# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Disallowed Expenses',
    'category': 'Accounting/Accounting',
    'summary': 'Manage disallowed expenses',
    'description': 'Manage disallowed expenses',
    'version': '1.0',
    'depends': ['account_reports'],
    'data': [
        'data/account_disallowed_expenses_report.xml',
        'security/ir.model.access.csv',
        'security/account_disallowed_expenses_security.xml',
        'views/account_account_views.xml',
        'views/account_disallowed_expenses_category_views.xml',
        'views/account_disallowed_expenses_report_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_disallowed_expenses/static/src/components/**/*',
        ],
    },
}
