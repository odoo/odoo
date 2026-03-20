# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import account_analytic_account
from . import mail_message
from . import project_project_stage
from . import project_task_recurrence
# `project_task_stage_personal` has to be loaded before `project_project` and `project_milestone`
from . import project_task_stage_personal
from . import project_milestone
from . import project_project
from . import project_role
from . import project_task
from . import project_task_type
from . import project_tags
from . import project_collaborator
from . import project_update
from . import res_config_settings
from . import res_partner
from . import res_users_settings
from . import res_users
from . import digest_digest
from . import ir_ui_menu
