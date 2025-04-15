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
    'at': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Belgium
    'be_comp': {
        'invoice_base_tag': 'l10n_be.tax_report_line_47_tag',
        'invoice_tax_tag': None,
        'refund_base_tag': 'l10n_be.tax_report_line_49_tag',
        'refund_tax_tag': None,
    },
    'be_asso': {
        'invoice_base_tag': 'l10n_be.tax_report_line_47_tag',
        'invoice_tax_tag': None,
        'refund_base_tag': 'l10n_be.tax_report_line_49_tag',
        'refund_tax_tag': None,
    },
    # Bulgaria
    'bg': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Croatia
    'hr': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Cyprus
    'cy': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Czech - Done in 13.0 - CoA not available yet
    'cz': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Denmark
    'dk': {
        'invoice_base_tag': 'l10n_dk.account_tax_report_line_section_b_products_non_eu_tag',
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Estonia - Done in 13.0 - CoA not available yet
    'ee': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Finland
    'fi': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # France
    'fr': {
        'invoice_base_tag': 'l10n_fr.tax_report_E3_tag',
        'invoice_tax_tag': None,
        'refund_base_tag': 'l10n_fr.tax_report_F8_tag',
        'refund_tax_tag': None,
    },
    # Germany SKR03
    'de_skr03': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Germany SKR04
    'de_skr04': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Greece
    'gr': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Hungary
    'hu': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Ireland
    'ie': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Italy
    'it': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Latvia
    'lv': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Lithuania
    'lt': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Luxembourg
    'lu': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Malta - Done in 13.0 - CoA not available yet
    'mt': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Netherlands
    'nl': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Poland
    'pl': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Portugal
    'pt': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Romania
    'ro': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Slovakia - Done in 13.0 - CoA not available yet
    'sk': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Slovenia
    'si': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Spain
    'es_assec': {
        'invoice_base_tag': "l10n_es.mod_303_casilla_124_balance",
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    'es_common': {
        'invoice_base_tag': "l10n_es.mod_303_casilla_124_balance",
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    'es_full': {
        'invoice_base_tag': "l10n_es.mod_303_casilla_124_balance",
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    'es_pymes': {
        'invoice_base_tag': "l10n_es.mod_303_casilla_124_balance",
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
    # Sweden
    'se': {
        'invoice_base_tag': None,
        'invoice_tax_tag': None,
        'refund_base_tag': None,
        'refund_tax_tag': None,
    },
}
