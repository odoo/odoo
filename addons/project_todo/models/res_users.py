# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models, modules, SUPERUSER_ID


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_activity_groups(self):
        """ Split To-do and Project activities in systray by removing
            the single project.task activity represented and doing a
            new query to split them between private/non-private tasks.
        """
        activity_groups = super()._get_activity_groups()
        # 1. removing project.task activity group
        to_remove = next((g for g in activity_groups if g.get('model') == 'project.task'), None)
        if to_remove:
            activity_groups.remove(to_remove)

        # 2. creating groups for todo and task seperately
        query = """SELECT BOOL(t.project_id) as is_task, count(*), act.res_model, act.res_id,
                       CASE
                           WHEN %(date)s - act.date_deadline::date = 0 THEN 'today'
                           WHEN %(date)s - act.date_deadline::date > 0 THEN 'overdue'
                           WHEN %(date)s - act.date_deadline::date < 0 THEN 'planned'
                        END AS states
                     FROM mail_activity AS act
                     JOIN project_task AS t ON act.res_id = t.id
                    WHERE act.res_model = 'project.task' AND act.user_id = %(user_id)s AND act.active in (TRUE, %(active)s)
                 GROUP BY is_task, states, act.res_model, act.res_id
                """
        self.env.cr.execute(query, {
            'date': str(fields.Date.context_today(self)),
            'user_id': self.env.uid,
            'active': self.env.context.get('active_test', True),
        })
        activity_data = self.env.cr.dictfetchall()
        view_type = self.env['project.task']._systray_view

        user_activities = {}
        for activity in activity_data:
            is_task = activity['is_task']
            if is_task not in user_activities:
                if not is_task:
                    module_name = 'project_todo'
                    name = _('To-Do')
                else:
                    module_name = 'project'
                    name = _('Task')
                icon = modules.Manifest.for_addon(module_name).icon
                user_activities[is_task] = {
                    'id': self.env['ir.model']._get('project.task').id,
                    'name': name,
                    'is_todo': not is_task,
                    'model': 'project.task',
                    'type': 'activity',
                    'icon': icon,
                    'domain': [('active', 'in', [True, False])],
                    'total_count': 0, 'today_count': 0, 'overdue_count': 0, 'planned_count': 0,
                    'res_ids': set(),
                    'view_type': view_type,
                }
            user_activities[is_task]['res_ids'].add(activity['res_id'])
            user_activities[is_task][f"{activity['states']}_count"] += activity['count']
            if activity['states'] in ('today', 'overdue'):
                user_activities[is_task]['total_count'] += activity['count']

        for group in user_activities.values():
            group.update({
                'domain': json.dumps([
                    ['active', 'in', [True, False]],
                    ['activity_ids.res_id', 'in', list(group['res_ids'])]
                ])
            })
        activity_groups.extend(list(user_activities.values()))

        return activity_groups

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
            self.env["project.task"].with_user(SUPERUSER_ID).with_context(mail_auto_subscribe_no_notify=True).create(create_vals)
