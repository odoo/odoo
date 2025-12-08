# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo import fields

from odoo.addons.project import _check_exists_collaborators_for_project_sharing
from odoo.tools.sql import SQL


def create_internal_project(env):
    # allow_timesheets is set by default, but erased for existing projects at
    # installation, as there is no analytic account for them.
    env['project.project'].search([]).write({'allow_timesheets': True})

    admin = env.ref('base.user_admin', raise_if_not_found=False)
    if not admin:
        return
    project_ids = env['res.company'].search([])._create_internal_project_task()
    env['account.analytic.line'].create([{
        'name': env._("Analysis"),
        'user_id': admin.id,
        'date': fields.datetime.today(),
        'unit_amount': 0,
        'project_id': task.project_id.id,
        'task_id': task.id,
    } for task in project_ids.task_ids.filtered(lambda t: t.company_id in admin.employee_ids.company_id)])

    _check_exists_collaborators_for_project_sharing(env)

def _uninstall_hook(env):

    def update_action_window(xmlid):
        act_window = env.ref(xmlid, raise_if_not_found=False)
        if act_window and act_window.domain and 'is_internal_project' in act_window.domain:
            act_window.domain = []

    update_action_window('project.open_view_project_all')
    update_action_window('project.open_view_project_all_group_stage')

    # archive the internal projects
    project_ids = env['res.company'].search([('internal_project_id', '!=', False)]).mapped('internal_project_id')
    if project_ids:
        project_ids.write({'active': False})

    env['ir.model.data'].search([('name', 'ilike', 'internal_project_default_stage')]).unlink()


def _pre_init_hook(env):
    """
    Create manually new compute+stored columns to allow installing the module on large databases without trigger an Out-of-memory error.
    """
    env.cr.execute(SQL("""
       ALTER TABLE account_analytic_line
       -- The task_id is set to False when there is no project_id on the line, but at installation,
       -- no line is associated with a project -> task_id = False
       ADD COLUMN IF NOT EXISTS task_id        INT4,
       -- At fresh installation, `task_id` is False -> parent_task_id, which is related to it, will also be False
       ADD COLUMN IF NOT EXISTS parent_task_id INT4,
       -- The project_id is defined as being the same as the one from the task, but task_id = False -> project_id = False
       ADD COLUMN IF NOT EXISTS project_id     INT4,
       -- The department_id is the one from the `employee_id`, but `employee_id` by default is False -> department_id = False
       ADD COLUMN IF NOT EXISTS department_id  INT4,
       -- The manager_id is the manager of the employee_id, but there is no `employee_id` by default -> manager_id = False
       ADD COLUMN IF NOT EXISTS manager_id     INT4
    """))
