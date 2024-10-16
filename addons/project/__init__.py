# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    AccountAnalyticAccount, DigestDigest, IrUiMenu, MailMessage,
    ProjectCollaborator, ProjectMilestone, ProjectProject, ProjectProjectStage, ProjectTags,
    ProjectTask, ProjectTaskRecurrence, ProjectTaskStagePersonal, ProjectTaskType, ProjectUpdate,
    ResConfigSettings, ResPartner,
)
from .report import ProjectTaskBurndownChartReport, ReportProjectTaskUser
from .wizard import (
    ProjectProjectStageDeleteWizard, ProjectShareCollaboratorWizard,
    ProjectShareWizard, ProjectTaskTypeDeleteWizard,
)

from odoo.tools.sql import create_index


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
        'mail_tracking_value_mail_message_id_old_value_integer_task_stage',
        env['mail.tracking.value']._table,
        ['mail_message_id', 'old_value_integer'],
        where=f'field_id={project_task_stage_field_id}'
    )

    # Create analytic plan fields on project model for existing plans
    env['account.analytic.plan'].search([])._sync_plan_column('project.project')
