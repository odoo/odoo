# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Nigeria - Accounting Reports',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting Reports for Nigeria
    """,
    'author': 'Odoo SA',
    'depends': [
        'l10n_ng',
        'account_reports',
    ],
    'data': [
        'data/tax_report.xml',
        'data/withholding_report.xml',
    ],
    'installable': True,
    'auto_install': [
        'l10n_ng',
        'account_reports',
    ],
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'l10n_ng_reports/static/src/components/**/*',
        ],
    }
}
