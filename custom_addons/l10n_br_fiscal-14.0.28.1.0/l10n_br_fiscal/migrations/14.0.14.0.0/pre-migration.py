# Copyright 2023 - TODAY Akretion - Raphael Valyi <raphael.valyi@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade

_field_renames = [
    (
        "res.company",
        "res_company",
        "simplifed_tax_id",
        "simplified_tax_id",
    ),
    (
        "res.company",
        "res_company",
        "simplifed_tax_range_id",
        "simplified_tax_range_id",
    ),
    (
        "res.company",
        "res_company",
        "simplifed_tax_percent",
        "simplified_tax_percent",
    ),
]


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    if not openupgrade.column_exists(env.cr, "res_company", "simplified_tax_id"):
        openupgrade.rename_fields(env, _field_renames)
