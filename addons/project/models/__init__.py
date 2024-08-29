# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .account_analytic_account import AccountAnalyticAccount
from .mail_message import MailMessage
from .project_project_stage import ProjectProjectStage
from .project_task_recurrence import ProjectTaskRecurrence
# `project_task_stage_personal` has to be loaded before `project_project` and `project_milestone`
from .project_task_stage_personal import ProjectTaskStagePersonal
from .project_milestone import ProjectMilestone
from .project_project import ProjectProject
from .project_task import ProjectTask
from .project_task_type import ProjectTaskType
from .project_tags import ProjectTags
from .project_collaborator import ProjectCollaborator
from .project_update import ProjectUpdate
from .res_config_settings import ResConfigSettings
from .res_partner import ResPartner
from .digest_digest import DigestDigest
from .ir_ui_menu import IrUiMenu
