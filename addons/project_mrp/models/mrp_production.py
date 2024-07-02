#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
from odoo import fields, models, _, api, Command
from odoo.osv.expression import AND


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    project_ids = fields.Many2many('project.project', compute='_compute_project_ids',
                                   store=True, copy=True, readonly=False, groups='project.group_project_user')
    project_count = fields.Integer(compute='_compute_project_count', groups='project.group_project_user')
    task_count = fields.Integer(compute='_compute_tasks_count')

    @api.depends('bom_id')
    def _compute_project_ids(self):
        for record in self:
            if record.bom_id.project_ids:
                record.project_ids = record.bom_id.project_ids

    @api.depends('project_ids', 'project_ids.task_count')
    def _compute_tasks_count(self):
        for production in self:
            production.task_count = sum(production.project_ids.mapped('task_count'))

    @api.depends('project_ids')
    def _compute_project_count(self):
        for production in self:
            production.project_count = len(production.project_ids)

    def action_view_linked_projects(self, show_created=False):
        self.ensure_one()
        if self.project_count == 1 or show_created:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Project'),
                'res_id': self.project_ids[-1].id,
                'res_model': 'project.project',
                'views': [(False, 'form')],
                'view_mode': 'kanban,tree,form'
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Projects'),
                'domain': [('id', 'in', self.project_ids.ids)],
                'res_model': 'project.project',
                'views': [(False, 'tree')],
                'view_mode': 'tree'
            }

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("project.action_view_task")
        action['context'] = {
            'default_project_id': self.project_ids[0].id,
            'default_user_ids': [self.env.uid],
        }
        action['domain'] = AND([ast.literal_eval(action['domain']), [('id', 'in', self.project_ids.task_ids.ids)]])
        return action

    def action_create_project(self):
        self.ensure_one()

        # The no_create_folder context key is used in documents_project
        self.env['project.project'].with_context(no_create_folder=True).create(
            self._prepare_project_values()
        )

        return self.action_view_linked_projects(True)

    def _prepare_project_values(self):
        self.ensure_one()
        return {
            'name': _('%s - Project', self.name),
            'active': True,
            'company_id': self.company_id.id,
            'user_id': False,
            'production_ids': [Command.link(self.id)],
            'type_ids': [
                Command.create({'name': name, 'fold': fold, 'sequence': sequence})
                for name, fold, sequence in [
                    (_('To Do'), False, 5),
                    (_('In Progress'), False, 10),
                    (_('Done'), False, 15),
                    (_('Cancelled'), True, 20),
                ]
            ]
        }
