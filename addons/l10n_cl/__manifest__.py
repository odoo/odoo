# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (c) 2019 - Blanco Martín & Asociados. https://www.bmya.cl
{
    'name': 'Chile - Accounting',
    'version': '3.0',
    'description': """
Chilean accounting chart and tax localization.
Plan contable chileno e impuestos de acuerdo a disposiciones vigentes
    """,
    'author': 'Blanco Martín & Asociados',
    'category': 'Localization',
    'depends': [
        'l10n_cl_base',
        'l10n_latam_document',
        ],
    'data': [
        'data/l10n_cl_chart_data.xml',
        'data/account_account_tags_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_tags_data.xml',
        'data/account_tax_data.xml',
        'data/l10n_latam.document.type.csv',
        'data/menuitem_data.xml',
        'data/product_data.xml',
        # 'data/product_uom.xml',
        'data/res.country.csv',
        'data/res_config_settings.xml',
        'data/res_partner.xml',
        'data/account_fiscal_template.xml',
        'data/account_chart_template_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
}
