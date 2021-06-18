# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard
from . import populate

from collections import defaultdict
from odoo import api, SUPERUSER_ID, _

def _generate_personal_stages(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    all_users = env.ref('project.group_project_user').users
    if not all_users:
        return

    all_tasks = env['project.task'].search([('user_id', 'in', all_users.ids)])
    user_tasks = defaultdict(lambda: env['project.task'])
    for task in all_tasks:
        user_tasks[task.user_id] |= task

    personal_stage_vals = []
    for user in all_users:
        stages = env['project.task.type'].create([{
            'name': _('Inbox'),
            'sequence': 10,
            'user_id': user.id,
        }, {
            'name': _('In Progress'),
            'sequence': 20,
            'user_id': user.id,
        }, {
            'name': _('Done'),
            'sequence': 30,
            'user_id': user.id,
        }])
        personal_stage_vals += [{
            'stage_id': stages[0].id,
            'user_id': user.id,
            'task_id': task.id,
        } for task in user_tasks[user]]
    if personal_stage_vals:
        env['project.personal.stage'].create(personal_stage_vals)
