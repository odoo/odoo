# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, modules, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_activity_groups(self):
        """ Split mass_mailing and mass_mailing_sms activities in systray by 
            removing the single mailing.mailing activity represented and
            doing a new query to split them by mailing_type.
        """
        activities = super()._get_activity_groups()
        view_type = self.env['mailing.mailing']._systray_view
        for activity in activities:
            if activity.get('model') == 'mailing.mailing':
                activities.remove(activity)
                query = """
                        WITH mailing_states AS (
                            SELECT m.mailing_type, act.res_id,
                                CASE
                                    WHEN %(today)s::date - MIN(act.date_deadline)::date = 0 Then 'today'
                                    WHEN %(today)s::date - MIN(act.date_deadline)::date > 0 Then 'overdue'
                                    WHEN %(today)s::date - MIN(act.date_deadline)::date < 0 Then 'planned'
                                END AS states
                            FROM mail_activity AS act
                            JOIN mailing_mailing AS m ON act.res_id = m.id
                            WHERE act.res_model = 'mailing.mailing' AND act.user_id = %(user_id)s AND act.active in (TRUE, %(active)s)
                            GROUP BY m.mailing_type, act.res_id
                        )
                        SELECT mailing_type, states, array_agg(res_id) AS res_ids, COUNT(res_id) AS count
                        FROM mailing_states
                        GROUP BY mailing_type, states
                        """
                self.env.cr.execute(query, {
                    'today': fields.Date.context_today(self),
                    'user_id': self.env.uid,
                    'active': self.env.context.get('active_test', True),
                })
                activity_data = self.env.cr.dictfetchall()

                user_activities = {}
                for act in activity_data:
                    if not user_activities.get(act['mailing_type']):
                        if act['mailing_type'] == 'sms':
                            module_name = 'mass_mailing_sms'
                            name = _('SMS Marketing')
                        else:
                            module_name = 'mass_mailing'
                            name = _('Email Marketing')
                        icon = modules.Manifest.for_addon(module_name).icon
                        res_ids = set()
                        user_activities[act['mailing_type']] = {
                            'id': self.env['ir.model']._get('mailing.mailing').id,
                            'name': name,
                            'model': 'mailing.mailing',
                            'type': 'activity',
                            'icon': icon,
                            'domain': [('active', 'in', [True, False])],
                            'total_count': 0, 'today_count': 0, 'overdue_count': 0, 'planned_count': 0,
                            'res_ids': res_ids,
                            "view_type": view_type,
                        }
                    user_activities[act['mailing_type']]['res_ids'].update(act['res_ids'])
                    user_activities[act['mailing_type']]['%s_count' % act['states']] += act['count']
                    if act['states'] in ('today', 'overdue'):
                        user_activities[act['mailing_type']]['total_count'] += act['count']

                for mailing_type in user_activities.keys():
                    user_activities[mailing_type].update({
                        'domain': json.dumps([
                            ['active', 'in', [True, False]],
                            ['activity_ids.res_id', 'in', list(user_activities[mailing_type]['res_ids'])],
                        ])
                    })
                activities.extend(list(user_activities.values()))
                break

        return activities
