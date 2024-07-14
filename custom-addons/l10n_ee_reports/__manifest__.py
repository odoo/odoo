# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Estonia - Accounting Reports',
    'version': '1.0',
    'countries': ['ee'],
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting Reports for Estonia
    """,
    'author': 'Odoo SA',
    'depends': [
        'l10n_ee',
        'account_reports',
    ],
    'data': [
        'views/report_export_templates.xml',
        'data/balance_sheet.xml',
        'data/profit_and_loss.xml',
        'data/ic_supply_report.xml',
        'data/tax_report.xml',
        'data/kmd_inf_report.xml',
    ],
    'installable': True,
    'auto_install': [
        'l10n_ee',
        'account_reports',
    ],
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
