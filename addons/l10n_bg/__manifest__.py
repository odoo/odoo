# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgaria - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['bg'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Chart accounting and taxes for Bulgaria
    """,
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'test_data': [
        'tests/data/account_chart_template.xml',
    ],
    'license': 'LGPL-3',
}
