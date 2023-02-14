# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, modules, _, _lt

class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def systray_get_activities(self):
        """ If user have not scheduled any note, it will not appear in activity menu.
            Making note activity always visible with number of notes on label. If there is no notes,
            activity menu not visible for note.
        """
        activities = super(Users, self).systray_get_activities()
        notes_count = self.env['project.task'].sudo().search_count([('user_ids', 'in', [self.env.uid])])
        if notes_count:
            note_index = next((index for (index, a) in enumerate(activities) if a["model"] == "project.task"), None)
            note_label = _("To-do")
            if note_index is not None:
                activities[note_index]['name'] = note_label
            else:
                activities.append({
                    'id': self.env['ir.model']._get('project.task').id,
                    'type': 'activity',
                    'name': note_label,
                    'model': 'project.task',
                    'icon': modules.module.get_module_icon(self.env['project.task']._original_module),
                    'total_count': 0,
                    'today_count': 0,
                    'overdue_count': 0,
                    'planned_count': 0
                })
        return activities

    @api.model_create_multi
    def create(self, vals_list):
        users = super(Users, self).create(vals_list)
        if not self.env.context.get('skip_onboarding_todo'):
            users.filtered(lambda user: not user.partner_share)._generate_onboarding_todo()
        return users

    def _generate_onboarding_todo(self):
        todos_to_create = []
        for user in self:
            self = self.with_context(lang=user.lang or self.env.user.lang)
            render_ctx = {'object': user}
            body = self.env['ir.qweb']._render(
                'note.todo_user_onboarding',
                render_ctx,
                minimal_qcontext=True,
                raise_if_not_found=False
            )
            if not body:
                break

            title = _lt('Welcome %s!', user.name)
            todos_to_create.append({
                'user_ids': [user.id],
                'description': body,
                'name': title,
            })

        if todos_to_create:
            self.env['project.task'].sudo().with_context(onboarding_todo_creation=True).create(todos_to_create)
