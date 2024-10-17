# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo.tools.sql import create_index

from .models.account_analytic_account import AccountAnalyticAccount
from .models.digest_digest import DigestDigest
from .models.ir_ui_menu import IrUiMenu
from .models.mail_message import MailMessage
from .models.project_collaborator import ProjectCollaborator
from .models.project_milestone import ProjectMilestone
from .models.project_project import ProjectProject
from .models.project_project_stage import ProjectProjectStage
from .models.project_tags import ProjectTags
from .models.project_task import ProjectTask
from .models.project_task_recurrence import ProjectTaskRecurrence
from .models.project_task_stage_personal import ProjectTaskStagePersonal
from .models.project_task_type import ProjectTaskType
from .models.project_update import ProjectUpdate
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .report.project_report import ReportProjectTaskUser
from .report.project_task_burndown_chart_report import ProjectTaskBurndownChartReport
from .wizard.project_project_stage_delete import ProjectProjectStageDeleteWizard
from .wizard.project_share_collaborator_wizard import ProjectShareCollaboratorWizard
from .wizard.project_share_wizard import ProjectShareWizard
from .wizard.project_task_type_delete import ProjectTaskTypeDeleteWizard


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
