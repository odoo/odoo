# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Mexico - Month 13 Trial Balance",
    "summary": "Mexico Month 13 Trial Balance Report",
    "version": "1.0",
    "author": "Vauxoo / Odoo",
    "category": "Accounting/Localizations/Reporting",
    "website": "http://www.odoo.com",
    "license": "OEEL-1",
    "depends": [
        "l10n_mx_reports",
    ],
    "data": [
        "views/account_move_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_mx_reports_closing/static/src/components/**/*',
        ],
        'web.assets_tests': [
            'l10n_mx_reports_closing/static/tests/tours/*',
        ],
    },
    "installable": True,
    "auto_install": True,
}
