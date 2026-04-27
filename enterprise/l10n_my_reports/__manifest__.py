# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Malaysia - Accounting Reports',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Base module for Malaysian reports
    """,
    'depends': [
        'l10n_my',
        'account_followup',
        'account_reports',
    ],
    'data': [
        "views/account_followup_views.xml",
        'views/res_config_settings_view.xml',
        "report/statement_account_templates.xml",
        "report/res_partner_reports.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_my_reports/static/src/**/*",
        ],
    },
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
