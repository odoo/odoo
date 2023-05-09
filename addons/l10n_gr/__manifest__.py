# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Greece - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['gr'],
    'author': 'P. Christeas, Odoo S.A.',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Greece.
==================================================================

Greek accounting chart and localization.
    """,
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
