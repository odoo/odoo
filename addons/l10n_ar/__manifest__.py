# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Argentinian Accounting',
    'version': '12.0.1.0.0',
    'description': """
Argentinian accounting chart and tax localization.
==================================================

* Define Argentinian chart of accounts:
  * Responsable Inscripto (RI)
  * Exento (EX)
  * Monotributo (Mono)
* Argentinian Taxes
* Fiscal Positions
* AFIP Legal Documents
* Add AFIP Codes for models
    * Currency
    * Country
    * Product Unit of Measure
    * Tax Group
    * Account Incoterms
    * Fiscal Position
    * Fiscal Position Template

Follow the next configuration steps

1. Go to your company and configure your CUIT number and AFIP Responsability
2. Go to Invoicing / Configuration and set the Chart of Account you will like
   to use.
3. Create your sale journals taking into account AFIP info if needed.
""",
    'author': ['ADHOC SA'],
    'category': 'Localization',
    'depends': [
        'l10n_latam_document',
        'l10n_ar_base',
    ],
    'data':[
        'data/account_account_tag_data.xml',
        'data/account_chart_base.xml',
        'data/account_chart_exento.xml',
        'data/account_chart_respinsc.xml',
        'data/account_tax_group.xml',
        'data/account_tax_template_data.xml',
        'data/res_country_group_data.xml',
        'data/account_fiscal_template.xml',
        'data/uom_uom_data.xml',
        'data/l10n_latam.document.type.csv',
        'data/res_partner_data.xml',
        'data/res_currency_data.xml',
        'data/res_country_data.xml',
        'data/product_product_data.xml',
        'data/account_incoterms_data.xml',
        # los cargamos con csv pero los hacemos no actualizables con un hook
        'views/account_move_line_view.xml',
        'views/account_move_view.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/afip_menuitem.xml',
        'views/res_currency_view.xml',
        'views/account_fiscal_position_view.xml',
        'views/uom_uom_view.xml',
        'views/account_journal_view.xml',
        'views/account_invoice_view.xml',
        'views/l10n_latam_document_type_view.xml',
        'security/security.xml',
    ],
    'demo': [
        'demo/exento_demo.xml',
        'demo/mono_demo.xml',
        'demo/respinsc_demo.xml',
    ],
    'post_init_hook': 'post_init_hook',
}
