# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Brazilian - Accounting',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/brazil.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['br'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Base module for the Brazilian localization
==========================================

This module consists of:

- Generic Brazilian chart of accounts
- Brazilian taxes such as:

  - IPI
  - ICMS
  - PIS
  - COFINS
  - ISS
  - IR
  - CSLL

- Document Types as NFC-e, NFS-e, etc.
- Identification Documents as CNPJ and CPF

The field tax_discount has also been added in the account.tax.template and
account.tax objects to allow the proper computation of some Brazilian VATs
such as ICMS. The chart of account creation wizard has been extended to
propagate those new data properly.

In addition to this module, the Brazilian Localizations is also
extended and complemented with several additional modules.

Brazil - Accounting Reports (l10n_br_reports)
---------------------------------------------
Adds a simple tax report that helps check the tax amount per tax group
in a given period of time. Also adds the P&L and BS adapted for the
Brazilian market.

Avatax Brazil (l10n_br_avatax)
------------------------------
Add Brazilian tax calculation via Avatax and all necessary fields needed to
configure Odoo in order to properly use Avatax and send the needed fiscal
information to retrieve the correct taxes.

Avatax for SOs in Brazil (l10n_br_avatax_sale)
----------------------------------------------
Same as the l10n_br_avatax module with the extension to the sales order module.
""",
    'author': 'Akretion, Odoo Brasil',
    'depends': [
        'account',
        'base_vat',
        'l10n_latam_base',
        'l10n_latam_invoice_document',
    ],
    'data': [
        'data/account_tax_report_data.xml',
        'data/l10n_latam.identification.type.csv',
        'data/l10n_latam.document.type.csv',
        'views/account_view.xml',
        'views/account_fiscal_position_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/account_journal_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
