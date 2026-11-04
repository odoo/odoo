# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Uruguay - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/uruguay.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['uy'],
    'version': '0.1',
    'author': 'Uruguay l10n Team, Guillem Barba, ADHOC',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
General Chart of Accounts.
==========================

This module adds accounting functionalities for the Uruguayan localization, representing the minimum required configuration for a company to operate in Uruguay under the regulations and guidelines provided by the DGI (Dirección General Impositiva).

Among the functionalities are:

* Uruguayan Generic Chart of Account
* Pre-configured VAT Taxes and Tax Groups.
* Legal document types in Uruguay.
* Valid contact identification types in Uruguay.
* Configuration and activation of Uruguayan Currencies  (UYU, UYI - Unidad Indexada Uruguaya).
* Frequently used default contacts already configured: DGI, Consumidor Final Uruguayo.

Configuration
-------------

Demo data for testing:

* Uruguayan company named "UY Company" with the Uruguayan chart of accounts already installed, pre configured taxes, document types and identification types.
* Uruguayan contacts for testing:

   * IEB Internacional
   * Consumidor Final Anónimo Uruguayo.

""",
    'depends': [
        'account',
        'l10n_latam_invoice_document',
        'l10n_latam_base',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
        'data/l10n_latam.document.type.csv',
        'data/l10n_latam_identification_type_data.xml',
        'data/res_partner_data.xml',
        'data/res_currency_data.xml',
        'views/account_tax_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/res_currency_rate_demo.xml',
    ],
    'license': 'LGPL-3',
}
