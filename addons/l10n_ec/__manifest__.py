# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ecuadorian Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ec'],
    'version': '3.9',
    'description': """
Functional
----------

This module adds accounting features for Ecuadorian localization, which
represent the minimum requirements to operate a business in Ecuador in compliance
with local regulation bodies such as the ecuadorian tax authority -SRI- and the
Superintendency of Companies -Super Intendencia de Compañías-

Follow the next configuration steps:
1. Go to your company and configure your country as Ecuador
2. Install the invoicing or accounting module, everything will be handled automatically

Highlights:
* Ecuadorian chart of accounts will be automatically installed, based on example provided by Super Intendencia de Compañías
* List of taxes (including withholds) will also be installed, you can switch off the ones your company doesn't use
* Fiscal position, document types, list of local banks, list of local states, etc, will also be installed

Technical
---------
Master Data:
* Chart of Accounts, based on recomendation by Super Cías
* Ecuadorian Taxes, Tax Tags, and Tax Groups
* Ecuadorian Fiscal Positions
* Document types (there are about 41 purchase documents types in Ecuador)
* Identification types
* Ecuador banks
* Partners: Consumidor Final, SRI, IESS, and also basic VAT validation
""",
    'author': 'TRESCLOUD (https://trescloud.com)',
    'category': 'Accounting/Localizations/Account Charts',
    'maintainer': 'TRESCLOUD',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/ecuador.html',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_iban',
        'account_debit_note',
        'l10n_latam_invoice_document',
        'l10n_latam_base',
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_tax_report_data.xml',
        'data/res.bank.csv',
        'data/l10n_latam_identification_type_data.xml',
        'data/res_partner_data.xml',
        'data/l10n_latam.document.type.csv',
        'data/l10n_ec.sri.payment.csv',
        'views/root_sri_menu.xml',
        'views/account_tax_view.xml',
        'views/l10n_latam_document_type_view.xml',
        'views/l10n_ec_sri_payment.xml',
        'views/account_journal_view.xml',
        "views/res_partner_view.xml",
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'installable': True,
}
