import logging

from odoo.db.schema import column_exists
from odoo.tools.module_data import rename_field, rename_in_stored_expressions

_logger = logging.getLogger(__name__)

RENAMES = (
    ("team.team", "assignment_optout", "lead_assignment_optout"),
    ("team.team", "assignment_domain", "lead_assignment_domain"),
    ("team.team", "assignment_max", "lead_assignment_max"),
    ("team.team", "assignment_enabled", "lead_assignment_enabled"),
    ("team.team", "assignment_auto_enabled", "lead_assignment_auto_enabled"),
    ("team.team", "alias_name", "lead_alias_name"),
    ("team.team", "alias_email", "lead_alias_email"),
    ("team.member", "assignment_optout", "lead_assignment_optout"),
    ("team.member", "assignment_domain", "lead_assignment_domain"),
    ("team.member", "assignment_domain_preferred", "lead_assignment_domain_preferred"),
    ("team.member", "assignment_max", "lead_assignment_max"),
    ("team.member", "assignment_enabled", "lead_assignment_enabled"),
)


def migrate(cr, version):
    if not version:
        return
    for model, old, new in RENAMES:
        rename_field(cr, model, old, new)
        rename_in_stored_expressions(cr, old, new, model=model)
        if model == "team.team":
            # leads, livechat steps and their templates reach the team by team_id
            rename_in_stored_expressions(cr, f"team_id.{old}", f"team_id.{new}")
    # before crm's data syncs the sale usage's aliases, or it creates empty
    # ones and the named aliases the teams had are left without an owner
    _adopt_lead_aliases(cr)


def _adopt_lead_aliases(cr):
    # crm.team carried one mixin.mail.alias per team, for leads; team.team
    # carries one team.alias per usage, and leads are the sale usage's
    if not column_exists(cr, "team_team", "alias_id"):
        return
    cr.execute(
        """
        INSERT INTO team_alias (team_id, usage, alias_id,
                                create_uid, create_date, write_uid, write_date)
        SELECT t.id, 'sale', t.alias_id, 1, now() AT TIME ZONE 'UTC',
               1, now() AT TIME ZONE 'UTC'
          FROM team_team t
         WHERE t.alias_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM team_alias a
                            WHERE a.team_id = t.id AND a.usage = 'sale')
        """
    )
    adopted = cr.rowcount
    cr.execute("ALTER TABLE team_team DROP COLUMN alias_id CASCADE")
    _logger.info("crm: %s team lead alias(es) became sale usage aliases", adopted)
