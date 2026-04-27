# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Philippines - Accounting Reports',
    "summary": """
Accounting reports for the Philippines
    """,
    "version": "1.0",
    "category": "Accounting/Localizations/Reporting",
    "license": "OEEL-1",
    "depends": [
        "l10n_ph",
        "account_reports",
    ],
    "data": [
        "data/sawt_qap_report.xml",
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
