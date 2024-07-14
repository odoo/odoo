# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report

def _uninstall_hook(env):
    role_menu = env.ref('planning.planning_menu_schedule_by_role', raise_if_not_found=False)
    if role_menu:
        role_menu.action = env.ref('planning.planning_action_schedule_by_role')
