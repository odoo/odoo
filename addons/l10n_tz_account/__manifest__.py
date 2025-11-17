# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tanzania - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['tz'],
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.0',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'description': """
    Tanzanian localisation containing:
    - COA
    - Taxes
    - Tax report
    - Fiscal position
    """,
    'data': [
        'data/l10n_tz_chart_data.xml',
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
