# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectTaskConvertSubtask(models.TransientModel):
    _name = 'project.task.convert.subtask.wizard'
    _description = 'Project Task Convert to Subtask Wizard'

    project_id = fields.Many2one('project.project', compute='_compute_project_id', help="Project of parent task",
        readonly=False)
    task_ids = fields.Many2many('project.task', string='Sub Tasks')
    parent_id = fields.Many2one('project.task', string='Parent Task', readonly=False, compute="_compute_parent_id",
        domain="[('id', 'not in', task_ids), ('project_id', '!=', False)]", store=True)

    @api.depends('project_id')
    def _compute_parent_id(self):
        for record in self:
            if record.project_id != record.parent_id.project_id:
                record.parent_id = False

    @api.depends('task_ids.project_id', 'parent_id')
    def _compute_project_id(self):
        for rocord in self:
            if rocord.parent_id:
                rocord.project_id = rocord.parent_id.project_id
            elif len(rocord.task_ids.project_id) == 1:
                rocord.project_id = rocord.task_ids.project_id
            else:
                rocord.project_id = False

    def action_update_parent(self):
        self.task_ids.filtered_domain(domain=['!', ('id', 'parent_of', self.parent_id.id)]).write({'parent_id': self.parent_id.id})
