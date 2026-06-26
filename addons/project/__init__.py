# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2
from odoo.tools import mute_logger
from . import controllers
from . import models
from . import report
from . import wizard


def _check_exists_collaborators_for_project_sharing(env):
    """ Check if it exists at least a collaborator in a shared project

        If it is the case we need to active the portal rules added only for this feature.
    """
    collaborator = env['project.collaborator'].search([], limit=1)
    if collaborator:
        # Then we need to enable the access rights linked to project sharing for the portal user
        env['project.collaborator']._toggle_project_sharing_portal_rules(True)


def _project_post_init(env):
    _check_exists_collaborators_for_project_sharing(env)

    # Create analytic plan fields on project model for existing plans
    env['account.analytic.plan'].search([])._sync_plan_column('project.project')

    # Auto-install project_duplicate if pgvector is available
    try:
        with mute_logger('odoo.sql_db'), env.cr.savepoint():
            env.cr.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            if not env.cr.fetchone():
                env.cr.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # If vector extension is verified/created, auto-install project_duplicate
        env['ir.module.module'].sudo().search([
            ('name', '=', 'project_duplicate'), ('state', '=', 'uninstalled')
        ]).button_install()
    except psycopg2.Error:
        pass


def _project_uninstall_hook(env):
    """Since the m2m table for the project share wizard's `partner_ids` field is not dropped at uninstall, it is
    necessary to ensure it is emptied, else re-installing the module will fail due to foreign keys constraints."""
    env['project.share.wizard'].search([("partner_ids", "!=", False)]).partner_ids = False
