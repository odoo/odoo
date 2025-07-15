# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import html2plaintext


class ProjectTask(models.Model):
    _inherit = 'project.task'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') and not vals.get('project_id') and not vals.get('parent_id'):
                if vals.get('description'):
                    # Generating name from first line of the description
                    text = html2plaintext(vals['description'])
                    name = text.strip().replace('*', '').partition("\n")[0]
                    vals['name'] = (name[:97] + '...') if len(name) > 100 else name
                else:
                    vals['name'] = self.env._('Untitled to-do')
        return super().create(vals_list)

    def action_convert_to_task(self):
        self.ensure_one()
        self.company_id = self.project_id.company_id
        return {
            'view_mode': 'form',
            'res_model': 'project.task',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
        }

    @api.model
    def get_todo_views_id(self):
        """ Returns the ids of the main views used in the To-Do app.

        :return: a list of views id and views type
                 e.g. [(kanban_view_id, "kanban"), (list_view_id, "list"), ...]
        :rtype: list(tuple())
        """
        return [
            (self.env['ir.model.data']._xmlid_to_res_id("project_todo.project_task_view_todo_kanban"), "kanban"),
            (self.env['ir.model.data']._xmlid_to_res_id("project_todo.project_task_view_todo_tree"), "list"),
            (self.env['ir.model.data']._xmlid_to_res_id("project_todo.project_task_view_todo_form"), "form"),
            (self.env['ir.model.data']._xmlid_to_res_id("project_todo.project_task_view_todo_calendar"), "calendar"),
            (self.env['ir.model.data']._xmlid_to_res_id("project_todo.project_task_view_todo_activity"), "activity"),
        ]
