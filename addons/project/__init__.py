# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo.tools.sql import create_index, make_identifier


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

    # Index to improve the performance of burndown chart.
    project_task_stage_field_id = env['ir.model.fields']._get_ids('project.task').get('stage_id')
    create_index(
        env.cr,
        make_identifier('mail_tracking_value_mail_message_id_old_value_integer_task_stage'),
        env['mail.tracking.value']._table,
        ['mail_message_id', 'old_value_integer'],
        where=f'field_id={project_task_stage_field_id}'
    )

    # Create analytic plan fields on project model for existing plans
    env['account.analytic.plan'].search([])._sync_plan_column('project.project')

    _migrate_email_templates_to_body_view(env)


def _migrate_email_templates_to_body_view(env):
    """Set body_view_id on existing templates without clearing body_html.

    This preserves user customizations while enabling view inheritance for new
    installs. Existing body_html takes priority over body_view_id.
    """
    template_view_mapping = [
        ('project.mail_template_data_project_task', 'project.email_body_project_task'),
        ('project.rating_project_request_email_template', 'project.email_body_rating_project_request'),
    ]
    for template_xmlid, view_xmlid in template_view_mapping:
        template = env.ref(template_xmlid, raise_if_not_found=False)
        view = env.ref(view_xmlid, raise_if_not_found=False)
        if template and view and not template.body_view_id:
            template.body_view_id = view

def _project_uninstall_hook(env):
    """Since the m2m table for the project share wizard's `partner_ids` field is not dropped at uninstall, it is
    necessary to ensure it is emptied, else re-installing the module will fail due to foreign keys constraints."""
    env['project.share.wizard'].search([("partner_ids", "!=", False)]).partner_ids = False
