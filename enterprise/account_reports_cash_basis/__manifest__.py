# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Cash Basis Accounting Reports',
    'summary': 'Add cash basis functionality for reports',
    'category': 'Accounting/Accounting',
    'description': """
Cash Basis for Accounting Reports
=================================
    """,
    'depends': ['account_reports'],
    'data': [
        'data/account_reports_data.xml',
        'views/account_report_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_reports_cash_basis/static/src/components/**/*',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
}
