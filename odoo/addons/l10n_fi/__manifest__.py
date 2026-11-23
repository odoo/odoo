# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Finnish Localization',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['fi'],
    'version': '13.0.2',
    'author': 'Avoin.Systems, Tawasta, Vizucom, Sprintit',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the Odoo module to manage the accounting in Finland.
============================================================

After installing this module, you'll have access to:
    * Finnish chart of account
    * Fiscal positions
    * Invoice Payment Reference Types (Finnish Standard Reference & Finnish Creditor Reference (RF))
    * Finnish Reference format for Sale Orders

Set the payment reference type from the Sales Journal.
    """,
    'depends': [
        'base_iban',
        'base_vat',
        'account',
    ],
    'data': [
        'data/account_account_tag_data.xml',
        'data/account_tax_report_line.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
