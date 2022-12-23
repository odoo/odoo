# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ireland - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ie'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
    This module is for all the Irish SMEs who would like to setup their accounting quickly. The module provides:

    - a Chart of Accounts customised to Ireland
    - VAT Rates and Structure""",
    'author': 'Target Integration (http://www.targetintegration.com)',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
