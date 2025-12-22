# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, Command
from odoo.tools import html2plaintext


class Task(models.Model):
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

    def _ensure_onboarding_todo(self):
        if not self.env.user.has_group('project_todo.group_onboarding_todo'):
            self._generate_onboarding_todo(self.env.user)
            onboarding_group = self.env.ref('project_todo.group_onboarding_todo').sudo()
            onboarding_group.write({'users': [Command.link(self.env.user.id)]})

    def _generate_onboarding_todo(self, user):
        user.ensure_one()
        self_lang = self.with_context(lang=user.lang or self.env.user.lang)
        body = self_lang.env['ir.qweb']._render(
            'project_todo.todo_user_onboarding',
            {'object': user},
            minimal_qcontext=True,
            raise_if_not_found=False
        )
        if not body:
            return
        title = self_lang.env._('Welcome %s!', user.name)
        self.env['project.task'].create([{
            'user_ids': user.ids,
            'description': body,
            'name': title,
        }])

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
            (self.env['ir.model.data']._xmlid_to_res_id("project_todo.project_task_view_todo_activity"), "activity"),
        ]
