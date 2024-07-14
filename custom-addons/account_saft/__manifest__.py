# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Standard Audit File for Tax Base module',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
Base module for SAF-T reporting
===============================
This is meant to be used with localization specific modules.
    """,
    'depends': [
        'account_reports'
    ],
    'data': [
        'data/saft_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_saft/static/src/components/**/*',
        ],
    },
    'license': 'OEEL-1',
}
