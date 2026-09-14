"""Move the timesheet rules off project followers.

They live in a ``noupdate`` block, so they are reloaded from
``security/hr_timesheet_security.xml`` onto ``project.project.user_has_access``.
The portal rule ships inactive and project collaborators switch it on, so it then
follows whether any collaborator exists.
"""

from odoo import SUPERUSER_ID, api
from odoo.tools.convert import reload_records

RULES = (
    "timesheet_line_rule_portal_user",
    "timesheet_line_rule_user",
    "timesheet_line_rule_approver",
    "timesheet_analysis_report_user",
    "timesheet_analysis_report_approver",
)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    reload_records(env, "hr_timesheet", "security/hr_timesheet_security.xml", RULES)
    collaborators = env["project.collaborator"]
    collaborators._update_project_sharing_portal_rules(
        bool(collaborators.search_count([], limit=1))
    )
