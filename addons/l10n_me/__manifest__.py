# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Montenegro - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['me'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Base module of the Montenegrin localization: chart of accounts, taxes, fiscal positions and VAT return.

The chart of accounts is based on the "Pravilnik o kontnom okviru i sadržini računa u kontnom okviru za
pravna lica registrovana za obavljanje privredne djelatnosti i druga pravna lica" (Službeni list Crne Gore 11/20).
The VAT return follows the form PR PDV-2 used from the tax period January 2025 (Službeni list Crne Gore 120/24).
    """,
    'author': 'Odoo S.A.',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
