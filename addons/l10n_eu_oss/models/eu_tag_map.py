# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
The EU_TAG_MAP answers the question: "which tag should I apply on the OSS tax repartition line?"

{
    'fiscal_country_code': {
        'invoice_base_tag': xml_id_of_the_tag or None,
        'invoice_tax_tag': xml_id_of_the_tag or None,
        'refund_base_tag': xml_id_of_the_tag or None,
        'refund_tax_tag': xml_id_of_the_tag or None,
    },
}
"""

EU_TAG_MAP = {
    # Austria
    'l10n_at.l10n_at_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Belgium
    'l10n_be.l10nbe_chart_template': {
        'invoice_base_tag': 'l10n_be.tax_report_line_47',
        'invoice_tax_tag': None,
        'refund_base_tag': 'l10n_be.tax_report_line_49',
        'refund_tax_tag': None,
    },
    # Bulgaria
    'BG': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Croatia
    'l10n_hr.l10n_hr_chart_template_rrif': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Cyprus
    'CY': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Czech - Done in 13.0 - CoA not available yet
    'l10n_cz.cz_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Denmark
    'l10n_dk.dk_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Estonia - Done in 13.0 - CoA not available yet
    'EE': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Finland
    'l10n_fi.fi_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # France
    'l10n_fr.l10n_fr_pcg_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Germany SKR03
    'l10n_de_skr03.l10n_de_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Germany SKR04
    'l10n_de_skr04.l10n_chart_de_skr04': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Greece
    'l10n_gr.l10n_gr_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Hungary
    'l10n_hu.hungarian_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Ireland
    'l10n_ie.l10n_ie': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Italy
    'l10n_it.l10n_it_chart_template_generic': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Latvia
    'LV': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Lithuania
    'l10n_lt.account_chart_template_lithuania': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Luxembourg
    'l10n_lu.lu_2011_chart_1': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Malta - Done in 13.0 - CoA not available yet
    'MT': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Netherlands
    'l10n_nl.l10nnl_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Poland
    'l10n_pl.pl_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Portugal
    'l10n_pt.pt_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Romania
    'l10n_ro.ro_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Slovakia - Done in 13.0 - CoA not available yet
    'l10n_sk.sk_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Slovenia
    'l10n_si.gd_chart': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Spain
    'l10n_es.account_chart_template_common': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Sweden
    'l10n_se.l10nse_chart_template': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
}
