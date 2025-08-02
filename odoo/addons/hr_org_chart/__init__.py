# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

def _uninstall_hook(env):
    def update_view_mode(view):
        act_window = env.ref(view, raise_if_not_found=False)
        if act_window and 'hierarchy' in act_window.view_mode:
            act_window.view_mode = ','.join(view_mode for view_mode in act_window.view_mode.split(',') if view_mode != 'hierarchy')

    update_view_mode('hr.hr_employee_public_action')
    update_view_mode('hr.hr_department_kanban_action')
    update_view_mode('hr.hr_department_tree_action')
    update_view_mode('hr.open_view_employee_list_my')
