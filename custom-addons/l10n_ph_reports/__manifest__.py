# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Philippines - Accounting Reports',
    "summary": """
Accounting reports for the Philippines
    """,
    "version": "1.0",
    "category": "Localization",
    "icon": "/base/static/img/country_flags/ph.png",
    "license": "OEEL-1",
    "depends": [
        "l10n_ph",
        "account_reports",
    ],
    "data": [
        "data/slsp_report.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_ph_reports/static/src/components/**/*',
        ],
    },
    "installable": True,
    "auto_install": True,
}
