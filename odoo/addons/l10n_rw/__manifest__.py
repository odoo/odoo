# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Rwanda - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['rw'],
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.0',
    'depends': [
        'account',
    ],
    'description': """
    Rwandan localisation containing:
    - COA
    - Taxes
    - Tax report
    - Fiscal position
    """,
    'data': [
        'data/l10n_rw_chart_data.xml',
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
