"""Project collaborators switch the portal timesheet rule on.

The rules themselves move onto ``project.project.user_has_access`` through the data files
(the pre-migrate releases their noupdate); the portal rule ships inactive, so it then
follows whether any collaborator exists.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    collaborators = api.Environment(cr, SUPERUSER_ID, {})["project.collaborator"]
    collaborators._update_project_sharing_portal_rules(
        bool(collaborators.search_count([], limit=1))
    )
