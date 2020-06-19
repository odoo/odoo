# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, modules, _


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def systray_get_activities(self):
        """ Split mass_mailing and mass_mailing_sms activities in systray by 
            removing the single mailing.mailing activity represented and
            doing a new query to split them by mailing_type.
        """
        activities = super(Users, self).systray_get_activities()
        for activity in activities:
            if activity.get('model') == 'mailing.mailing':
                activities.remove(activity)
                query = """SELECT m.mailing_type, count(*), act.res_model as model, act.res_id,
                            CASE
                                WHEN %(today)s::date - act.date_deadline::date = 0 Then 'today'
                                WHEN %(today)s::date - act.date_deadline::date > 0 Then 'overdue'
                                WHEN %(today)s::date - act.date_deadline::date < 0 Then 'planned'
                            END AS states
                        FROM mail_activity AS act
                        JOIN mailing_mailing AS m ON act.res_id = m.id
                        WHERE act.res_model = 'mailing.mailing' AND act.user_id = %(user_id)s  
                        GROUP BY m.mailing_type, states, act.res_model, act.res_id;
                        """
                self.env.cr.execute(query, {
                    'today': fields.Date.context_today(self),
                    'user_id': self.env.uid,
                })
                activity_data = self.env.cr.dictfetchall()
                
                user_activities = {}
                for act in activity_data:
                    if not user_activities.get(act['mailing_type']):
                        if act['mailing_type'] == 'sms':
                            module = 'mass_mailing_sms'
                            name = _('SMS Marketing')
                        else:
                            module = 'mass_mailing'
                            name = _('Email Marketing')
                        icon = module and modules.module.get_module_icon(module)
                        res_ids = set()
                        user_activities[act['mailing_type']] = {
                            'name': name,
                            'model': 'mailing.mailing',
                            'type': 'activity',
                            'icon': icon,
                            'total_count': 0, 'today_count': 0, 'overdue_count': 0, 'planned_count': 0,
                            'res_ids': res_ids,
                        }
                    user_activities[act['mailing_type']]['res_ids'].add(act['res_id'])
                    user_activities[act['mailing_type']]['%s_count' % act['states']] += act['count']
                    if act['states'] in ('today', 'overdue'):
                        user_activities[act['mailing_type']]['total_count'] += act['count']

                for mailing_type in user_activities.keys():
                    user_activities[mailing_type].update({
                        'actions': [{'icon': 'fa-clock-o', 'name': 'Summary',}],
                        'domain': json.dumps([['activity_ids.res_id', 'in', list(user_activities[mailing_type]['res_ids'])]])
                    })
                activities.extend(list(user_activities.values()))
                break

        return activities
