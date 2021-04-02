# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (c) 2019 - Blanco Martín & Asociados. https://www.bmya.cl
{
    'name': 'Chile - Accounting',
    'version': "3.0",
    'description': """
Chilean accounting chart and tax localization.
Plan contable chileno e impuestos de acuerdo a disposiciones vigentes
    """,
    'author': 'Blanco Martín & Asociados',
    'category': 'Accounting/Localizations/Account Charts',
    'website': 'https://www.odoo.com/documentation/user/14.0/accounting/fiscal_localizations/localizations/chile.html',
    'depends': [
        'contacts',
        'base_address_city',
        'base_vat',
        'l10n_latam_base',
        'l10n_latam_invoice_document',
        'uom',
        ],
    'data': [
        'views/account_move_view.xml',
        'views/account_tax_view.xml',
        'views/ir_sequence_view.xml',
        'views/res_bank_view.xml',
        'views/res_country_view.xml',
        'views/report_invoice.xml',
        'views/res_partner.xml',
        'views/res_config_settings_view.xml',
        'data/l10n_cl_chart_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_tags_data.xml',
        'data/account_tax_data.xml',
        'data/l10n_latam_identification_type_data.xml',
        'data/l10n_latam.document.type.csv',
        'data/menuitem_data.xml',
        'data/product_data.xml',
        'data/uom_data.xml',
        'data/res.currency.csv',
        'data/res_currency_data.xml',
        'data/res.bank.csv',
        'data/res.country.csv',
        'data/res_partner.xml',
        'data/account_fiscal_template.xml',
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/partner_demo.xml',
    ]
}
