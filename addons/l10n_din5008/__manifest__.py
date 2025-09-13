# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DIN 5008',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'description': "This is the base module that defines the DIN 5008 standard in Odoo.",
    'depends': ['account'],
    'data': [
        'report/din5008_report.xml',
        'report/din5008_account_move_layout.xml',
        'data/report_layout.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_din5008/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
