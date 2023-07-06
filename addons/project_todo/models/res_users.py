# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, modules, _


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def systray_get_activities(self):
        """ Split project and project_todo activities in systray by 
            removing the single project.task activity represented and
            doing a new query to split them in private tasks and other
            tasks.
        """
        activities = super(Users, self).systray_get_activities()
        for activity in activities:
            if activity.get('model') == 'project.task':
                activities.remove(activity)
                query = """SELECT count(*), act.res_model as model, act.res_id,
                            CASE
                                WHEN %(today)s::date - act.date_deadline::date = 0 THEN 'today'
                                WHEN %(today)s::date - act.date_deadline::date > 0 THEN 'overdue'
                                WHEN %(today)s::date - act.date_deadline::date < 0 THEN 'planned'
                            END AS states,
                            CASE
                                WHEN t.project_root_id IS NULL THEN true
                                ELSE false
                            END AS is_private
                        FROM mail_activity AS act
                        JOIN project_task AS t ON act.res_id = t.id
                        WHERE act.res_model = 'project.task' AND act.user_id = %(user_id)s  
                        GROUP BY t.project_root_id, states, act.res_model, act.res_id;
                        """
                self.env.cr.execute(query, {
                    'today': fields.Date.context_today(self),
                    'user_id': self.env.uid,
                })
                activity_data = self.env.cr.dictfetchall()
                
                user_activities = {}
                for act in activity_data:
                    if not user_activities.get(act['is_private']):
                        if act['is_private']:
                            module = 'project_todo'
                            name = _('To-Do')
                        else:
                            module = 'project'
                            name = _('Task')
                        icon = module and modules.module.get_module_icon(module)
                        res_ids = set()
                        user_activities[act['is_private']] = {
                            'id': self.env['ir.model']._get('project.task').id,
                            'name': name,
                            'model': 'project.task',
                            'type': 'activity',
                            'icon': icon,
                            'total_count': 0, 'today_count': 0, 'overdue_count': 0, 'planned_count': 0,
                            'res_ids': res_ids,
                        }
                    user_activities[act['is_private']]['res_ids'].add(act['res_id'])
                    user_activities[act['is_private']]['%s_count' % act['states']] += act['count']
                    if act['states'] in ('today', 'overdue'):
                        user_activities[act['is_private']]['total_count'] += act['count']

                for is_private in user_activities.keys():
                    user_activities[is_private].update({
                        'actions': [{'icon': 'fa-clock-o', 'name': 'Summary',}],
                        'domain': json.dumps([['activity_ids.res_id', 'in', list(user_activities[is_private]['res_ids'])]])
                    })
                activities.extend(list(user_activities.values()))
                break

        return activities
