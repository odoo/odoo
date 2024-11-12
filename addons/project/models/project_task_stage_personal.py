# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectTaskStagePersonal(models.Model):
    _name = 'project.task.stage.personal'
    _description = 'Personal Task Stage'
    _table = 'project_task_user_rel'
    _rec_name = 'stage_id'

    task_id = fields.Many2one('project.task', required=True, ondelete='cascade', index=True, export_string_translation=False)
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True, export_string_translation=False)
    stage_id = fields.Many2one('project.task.type', domain="[('user_id', '=', user_id)]", ondelete='set null', export_string_translation=False)

    _project_personal_stage_unique = models.Constraint(
        'UNIQUE (task_id, user_id)',
        'A task can only have a single personal stage per user.',
    )
