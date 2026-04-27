# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import report


def _uninstall_hook(env):
    resource_menu = env.ref('planning.planning_menu_schedule_by_resource', raise_if_not_found=False)
    if resource_menu:
        resource_menu.action = env.ref('planning.planning_action_schedule_by_resource')
