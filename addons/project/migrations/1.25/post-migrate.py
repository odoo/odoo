"""Carry follower-based access onto collaborators and team members.

Following a project used to grant access to it. Access is now explicit, so what
followers had becomes a grant of the same reach:

* a collaborator's ``limited_access`` becomes ``edit`` when set and
  ``advanced_edit`` when not, the modes that keep what it could edit;
* a portal contact following a project shared with portal users was a read-only
  collaborator in all but name, and becomes a ``view`` collaborator;
* an internal user following any project becomes a team member, so a project
  that is or later turns private keeps admitting them.

The record rules that read followers live in a ``noupdate`` block, so they are
reloaded from ``security/project_security.xml`` onto ``user_has_access``; the
project-sharing rule and ACL then follow whether any collaborator now exists.
"""

import logging

from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists
from odoo.tools.convert import reload_records

_logger = logging.getLogger(__name__)

RULES = (
    "project_public_members_rule",
    "project_project_rule_portal",
    "task_visibility_rule",
    "task_visibility_rule_project_user",
    "workflow_step_visibility_rule",
    "workflow_step_rule_portal_project_sharing",
    "collaborator_visibility_rule",
    "project_task_rule_portal",
    "project_task_rule_portal_project_sharing",
    "update_visibility_rule",
    "report_project_task_user_rule",
    "burndown_chart_project_user_rule",
    "cfd_report_project_user_rule",
    "milestone_visibility_rule",
    "project_milestone_rule_portal_project_sharing",
)


def migrate(cr, version):
    if not version:
        return
    if column_exists(cr, "project_collaborator", "limited_access"):
        cr.execute(
            """
            UPDATE project_collaborator
               SET access_mode = CASE WHEN limited_access THEN 'edit'
                                      ELSE 'advanced_edit' END
            """
        )
        _logger.info("project: %s collaborator access modes set", cr.rowcount)

    cr.execute(
        """
        INSERT INTO project_collaborator
               (project_id, partner_id, access_mode,
                create_uid, write_uid, create_date, write_date)
        SELECT DISTINCT follower.res_id, follower.partner_id, 'view',
               %s, %s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC'
          FROM mail_followers follower
          JOIN project_project project ON project.id = follower.res_id
          JOIN res_partner partner ON partner.id = follower.partner_id
         WHERE follower.res_model = 'project.project'
           AND project.privacy_visibility IN ('invited_users', 'portal')
           AND project.is_template IS NOT TRUE
           AND partner.partner_share
           AND NOT EXISTS (
                   SELECT 1 FROM project_collaborator collaborator
                    WHERE collaborator.project_id = follower.res_id
                      AND collaborator.partner_id = follower.partner_id
               )
        """,
        (SUPERUSER_ID, SUPERUSER_ID),
    )
    _logger.info("project: %s portal followers became view collaborators", cr.rowcount)

    cr.execute(
        """
        INSERT INTO project_project_member_user_rel (project_id, user_id)
        SELECT DISTINCT follower.res_id, users.id
          FROM mail_followers follower
          JOIN res_users users ON users.partner_id = follower.partner_id
         WHERE follower.res_model = 'project.project'
           AND users.share IS NOT TRUE
        ON CONFLICT DO NOTHING
        """
    )
    _logger.info("project: %s internal followers became team members", cr.rowcount)

    env = api.Environment(cr, SUPERUSER_ID, {})
    reload_records(env, "project", "security/project_security.xml", RULES)
    collaborators = env["project.collaborator"]
    collaborators._update_project_sharing_portal_rules(
        bool(collaborators.search_count([], limit=1))
    )
