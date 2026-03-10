# Copyright (C) 2024 - TODAY Renato Lima - Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade

_xml_ids_tax_definition_icms_renames = [
    (
        "l10n_br_fiscal.tax_icms_regulation_ac_ac_17_default",
        "l10n_br_fiscal.tax_icms_regulation_ac_ac_19_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_al_al_17_default",
        "l10n_br_fiscal.tax_icms_regulation_al_al_19_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_am_am_18_default",
        "l10n_br_fiscal.tax_icms_regulation_am_am_20_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_ba_ba_18_default",
        "l10n_br_fiscal.tax_icms_regulation_ba_ba_20_50_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_ce_ce_18_default",
        "l10n_br_fiscal.tax_icms_regulation_ce_ce_20_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_df_df_18_default",
        "l10n_br_fiscal.tax_icms_regulation_df_df_20_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_go_go_17_default",
        "l10n_br_fiscal.tax_icms_regulation_go_go_19_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_ma_ma_18_default",
        "l10n_br_fiscal.tax_icms_regulation_ma_ma_22_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_pa_pa_17_default",
        "l10n_br_fiscal.tax_icms_regulation_pa_pa_19_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_pb_pb_18_default",
        "l10n_br_fiscal.tax_icms_regulation_pb_pb_20_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_pr_pr_18_default",
        "l10n_br_fiscal.tax_icms_regulation_pr_pr_19_50_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_pe_pe_18_default",
        "l10n_br_fiscal.tax_icms_regulation_pe_pe_20_50_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_pi_pi_18_default",
        "l10n_br_fiscal.tax_icms_regulation_pi_pi_21_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_rj_rj_20_default",
        "l10n_br_fiscal.tax_icms_regulation_rj_rj_22_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_rs_rs_18_default",
        "l10n_br_fiscal.tax_icms_regulation_rs_rs_17_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_ro_ro_17_5_default",
        "l10n_br_fiscal.tax_icms_regulation_ro_ro_19_50_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_rr_rr_17_default",
        "l10n_br_fiscal.tax_icms_regulation_rr_rr_20_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_se_se_18_default",
        "l10n_br_fiscal.tax_icms_regulation_se_se_19_default",
    ),
    (
        "l10n_br_fiscal.tax_icms_regulation_to_to_18_default",
        "l10n_br_fiscal.tax_icms_regulation_to_to_20_default",
    ),
]


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _xml_ids_tax_definition_icms_renames)
