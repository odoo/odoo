# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgaria - Accounting',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['bg'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Chart accounting and taxes for Bulgaria
    """,
    'depends': [
        'account',
        'base_vat',
    ],
    'data': [
        'data/tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
