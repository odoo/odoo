# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Argentinian Accounting',
    'version': "3.0",
    'description': """
Functional
----------

This module add accounting features for the Argentinian localization, which represent the minimal configuration needed for a company  to operate in Argentina and under the AFIP (Administración Federal de Ingresos Públicos) regulations and guidelines.

Follow the next configuration steps for Production:

1. Go to your company and configure your VAT number and AFIP Responsibility Type
2. Go to Accounting / Settings and set the Chart of Account that you will like to use.
3. Create your Sale journals taking into account AFIP POS info.

Demo data for testing:

* 3 companies were created, one for each AFIP responsibility type with the respective Chart of Account installed. Choose the company that fix you in order to make tests:

  * (AR) Responsable Inscripto
  * (AR) Exento
  * (AR) Monotributo

* Journal sales configured to Pre printed and Expo invoices in all companies
* Invoices and other documents examples already validated in “(AR) Responsable Inscripto” company
* Partners example for the different responsibility types:

  * ADHOC (IVA Responsable Inscripto)
  * Consejo Municipal Rosario (IVA Sujeto Exento)
  * Gritti (Monotributo)
  * Cerro Castor. IVA Liberado in Zona Franca
  * Expresso (Cliente del Exterior)
  * Odoo (Proveedor del Exterior)

Highlights:

* Chart of account will not be automatically installed, each CoA Template depends on the AFIP Responsibility of the company, you will need to install the CoA for your needs.
* No sales journals will be generated when installing a CoA, you will need to configure your journals manually.
* The Document type will be properly pre selected when creating an invoice depending on the fiscal responsibility of the issuer and receiver of the document and the related journal.
* A CBU account type has been added and also CBU Validation


Technical
---------

This module adds both models and fields that will be eventually used for the electronic invoice module. Here is a summary of the main features:

Master Data:

* Chart of Account: one for each AFIP responsibility that is related to a legal entity:

  * Responsable Inscripto (RI)
  * Exento (EX)
  * Monotributo (Mono)

* Argentinian Taxes and Account Tax Groups (VAT taxes with the existing aliquots and other types)
* AFIP Responsibility Types
* Fiscal Positions (in order to map taxes)
* Legal Documents Types in Argentina
* Identification Types valid in Argentina.
* Country AFIP codes and Country VAT codes for legal entities, natural persons and others
* Currency AFIP codes
* Unit of measures AFIP codes
* Partners: Consumidor Final and AFIP
""",
    'author': 'ADHOC SA',
    'category': 'Localization',
    'depends': [
        'l10n_latam_invoice_document',
        'l10n_latam_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_latam_identification_type_data.xml',
        'data/l10n_ar_afip_responsibility_type_data.xml',
        'data/account_group_data.xml',
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_data2.xml',
        'data/account_tax_group.xml',
        'data/account_tax_template_data.xml',
        'data/account_fiscal_template.xml',
        'data/uom_uom_data.xml',
        'data/l10n_latam.document.type.csv',
        'data/res_partner_data.xml',
        'data/res.currency.csv',
        'data/res.country.csv',
        'views/account_move_view.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/res_country_view.xml',
        'views/afip_menuitem.xml',
        'views/l10n_ar_afip_responsibility_type_view.xml',
        'views/res_currency_view.xml',
        'views/account_fiscal_position_view.xml',
        'views/uom_uom_view.xml',
        'views/account_journal_view.xml',
        'views/l10n_latam_document_type_view.xml',
        'views/ir_sequence_view.xml',
        'views/report_invoice.xml',
        'report/invoice_report_view.xml',
    ],
    'demo': [
        # we create demo data on different companies (not main_company) to
        # allow different setups and also to allow multi-localization demo data
        'demo/exento_demo.xml',
        'demo/mono_demo.xml',
        'demo/respinsc_demo.xml',
        'demo/res_partner_demo.xml',
        'demo/account_tax_template_demo.xml',
        'demo/product_product_demo.xml',
        'demo/account_customer_invoice_demo.xml',
        'demo/account_customer_refund_demo.xml',
        'demo/account_supplier_invoice_demo.xml',
        'demo/account_supplier_refund_demo.xml',
        # restore
        'demo/res_users_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
