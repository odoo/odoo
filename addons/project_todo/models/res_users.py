# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, models, modules, SUPERUSER_ID


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_activity_groups(self):
        """Override to split the single 'project.task' activity group.

        This method intercepts all task-related activities and divides them
        into two distinct groups for the systray:
        - **To-Do**: Tasks not linked to a project (`project_id` is False).
        - **Task**: Tasks linked to a project (`project_id` is True).
        """
        groups = super()._get_activity_groups()

        task_group = next((g for g in groups if g['model'] == 'project.task'), None)
        if not task_group:
            return groups
        groups.remove(task_group)

        all_activities = self.env['mail.activity'].browse(task_group['activity_ids'])

        task_ids = all_activities.mapped('res_id')
        tasks = self.env['project.task'].browse(task_ids)
        is_todo_map = {t.id: not t.project_id for t in tasks}

        todo_activities = all_activities.filtered(lambda a: is_todo_map.get(a.res_id))
        task_activities = all_activities - todo_activities

        if todo_activities:
            todo_group = self._format_activity_group('project.task', todo_activities)
            todo_group.update({
                'name': _('To-Do'),
                'is_todo': True,
                'icon': modules.module.get_module_icon('project_todo'),
                'domain': [("active", "in", [True, False]), ("project_id", "=", False)],
            })
            groups.append(todo_group)

        if task_activities:
            project_group = self._format_activity_group('project.task', task_activities)
            project_group.update({
                'is_todo': False,
                'domain': [("active", "in", [True, False]), ("project_id", "!=", False)],
            })
            groups.append(project_group)

        return groups

    def _onboard_users_into_project(self, users):
        res = super()._onboard_users_into_project(users)
        if res:
            res._generate_onboarding_todo()

    def _generate_onboarding_todo(self):
        create_vals = []
        for user in self:
            self_lang = self.with_context(lang=user.lang or self.env.user.lang)
            body = self_lang.env["ir.qweb"]._render(
                "project_todo.todo_user_onboarding",
                {"object": user},
                minimal_qcontext=True,
                raise_if_not_found=False
            )
            if not body:
                continue
            title = self_lang.env._("Welcome %s!", user.name)
            create_vals.append({
                "user_ids": user.ids,
                "description": body,
                "name": title,
            })
        if create_vals:
            self.env["project.task"].with_user(SUPERUSER_ID).with_context({'mail_auto_subscribe_no_notify': True}).create(create_vals)
