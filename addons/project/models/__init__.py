# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import analytic_account
from . import analytic_account_tag
from . import project_milestone
from . import project_project_stage
from . import project_task_recurrence
# `project_task_stage_personal` has to be loaded before `project`
from . import project_task_stage_personal
from . import project
from . import project_collaborator
from . import project_update
from . import res_config_settings
from . import res_partner
from . import digest
from . import ir_ui_menu
