# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard
from . import populate

from odoo import api, SUPERUSER_ID
from odoo.tools.sql import create_index


def _check_exists_collaborators_for_project_sharing(env):
    """ Check if it exists at least a collaborator in a shared project

        If it is the case we need to active the portal rules added only for this feature.
    """
    collaborator = env['project.collaborator'].search([], limit=1)
    if collaborator:
        # Then we need to enable the access rights linked to project sharing for the portal user
        env['project.collaborator']._toggle_project_sharing_portal_rules(True)


def _project_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _check_exists_collaborators_for_project_sharing(env)

    # Index to improve the performance of burndown chart.
    project_task_stage_field_id = env['ir.model.fields']._get_ids('project.task').get('stage_id')
    create_index(
        cr,
        'mail_tracking_value_mail_message_id_old_value_integer_task_stage',
        env['mail.tracking.value']._table,
        ['mail_message_id', 'old_value_integer'],
        where=f'field={project_task_stage_field_id}'
    )

def _project_uninstall_hook(cr, registry):
    """Since the m2m table for the project share wizard's `partner_ids` field is not dropped at uninstall, it is
    necessary to ensure it is emptied, else re-installing the module will fail due to foreign keys constraints."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['project.share.wizard'].search([("partner_ids", "!=", False)]).partner_ids = False
