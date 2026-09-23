import logging

from odoo.db.schema import column_exists, table_exists
from odoo.tools.module_data import (
    remove_xmlid_records,
    rename_field,
    rename_in_stored_expressions,
    rename_model,
)

from odoo.addons.base.models.ir_access_convert import delete_converted_rows

_logger = logging.getLogger(__name__)

SALES_TEAM_RULES = (
    "sale_team_comp_rule",
    "crm_team_member_comp_rule",
    "crm_team_member_rule_personal",
    "crm_team_member_rule_all",
)


def _remove_sales_team_rules(cr):
    remove_xmlid_records(cr, "sale_team", SALES_TEAM_RULES)
    # base 1.97 converted a rule with several groups into one row per group,
    # `<rule>_<group>`, and those rows carry no external id of the rule itself
    for name in SALES_TEAM_RULES:
        delete_converted_rows(cr, "sale_team", name, logger=_logger)


def pre_init_hook(env):
    cr = env.cr
    if not table_exists(cr, "crm_team"):
        return
    # crm.team.member first: crm_team is a prefix of crm_team_member
    rename_model(cr, "crm.team.member", "team.member")
    rename_field(cr, "team.member", "crm_team_id", "team_id")
    rename_model(cr, "crm.team", "team.team")
    for model, old, new in (
        ("team.team", "crm_team_member_ids", "team_member_ids"),
        ("team.team", "crm_team_member_all_ids", "team_member_all_ids"),
        ("res.users", "crm_team_member_ids", "team_member_ids"),
        ("res.users", "crm_team_ids", "sale_team_ids"),
    ):
        rename_field(cr, model, old, new)
    # every field of these names is renamed, on these models and on pos, livechat
    # and member models alike, and rules reach them through paths from elsewhere
    for old, new in (
        ("crm_team_member_all_ids", "team_member_all_ids"),
        ("crm_team_member_ids", "team_member_ids"),
        ("crm_team_ids", "sale_team_ids"),
        ("crm_team_id", "team_id"),
    ):
        rename_in_stored_expressions(cr, old, new, unique=True)
    _remove_sales_team_rules(cr)
    # crm's mixin.mail.alias made alias_id required on every crm.team; teams
    # created before crm moves that alias onto team.alias must not need one
    if column_exists(cr, "team_team", "alias_id"):
        cr.execute("ALTER TABLE team_team ALTER COLUMN alias_id DROP NOT NULL")
    # every team a crm.team was is a sales team; sale_team adopts the column
    if not column_exists(cr, "team_team", "use_sale"):
        cr.execute("ALTER TABLE team_team ADD COLUMN use_sale boolean")
        cr.execute("UPDATE team_team SET use_sale = true")
