# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com)

{
    'name': 'Argentina - Accounting',
    'version': '12.0.1.0.0',
    'description': """
Argentinian accounting chart and tax localization.
==================================================

* Define Argentinian chart of accounts:
  * Responsable Inscripto (RI)
* Argentian Taxes
* Fiscal Positions
* AFIP Defined Legal Documents
* AFIP Incoterms
* Add AFIP Codes for models
    * Currency
    * Country
    * Product Unit of Measure
    * Tax Group
    * Fiscal Position
    * Fiscal Position Template
""",
    'author': ['ADHOC SA'],
    'category': 'Localization',
    'depends': [
        'l10n_latam_documents',
        'l10n_ar_base',
    ],
    'data':[
        'data/account_account_tag_data.xml',
        'data/account_chart_template.xml',
        'data/account_chart_base.xml',
        'data/account_chart_exento.xml',
        'data/account_chart_respinsc.xml',
        'data/account_tax_group.xml',
        'data/account_tax_template.xml',
        'data/res_country_group_data.xml',
        'data/account_fiscal_template.xml',
        'data/uom_uom.xml',
        'data/base_validator_data.xml',
        'data/l10n_latam.document.type.csv',
        'data/res_partner_data.xml',
        'data/res_currency_data.xml',
        'data/l10n_ar_afip_vat_f2002_category_data.xml',
        'data/res_country_data.xml',
        'data/menuitem.xml',
        'data/product_data.xml',
        'data/l10n_ar_afip_incoterm.xml',
        # los cargamos con csv pero los hacemos no actualizables con un hook
        'views/account_move_line_view.xml',
        'views/account_move_view.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/afip_menuitem.xml',
        'views/l10n_ar_afip_incoterm_view.xml',
        'views/account_account_view.xml',
        'views/res_currency_view.xml',
        'views/account_fiscal_position_view.xml',
        'views/uom_uom_view.xml',
        'views/account_journal_view.xml',
        'views/account_invoice_view.xml',
        'views/l10n_latam_document_type_view.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'demo': [
    ],
    'post_init_hook': 'post_init_hook',
}
