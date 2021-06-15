# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.tools.misc import formatLang

class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        return {
            **super(ProjectUpdate, self)._get_template_values(project),
            'people': self._get_people_values(project),
        }

    @api.model
    def _get_people_values(self, project):
        return {
            'uom': self.env.company._timesheet_uom_text(),
            'is_uom_hour': self.env.company._is_timesheet_hour_uom(),
            'activities': self._get_activities(project)
        }

    @api.model
    def _get_activities(self, project):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_user'):
            return []
        today = fields.Date.context_today(self)
        query = """
                SELECT timesheet.employee_id as employee_id,
                       gs::date as period,
                       sum(timesheet.unit_amount) as unit_amount,
                       employee.name as name
                  FROM project_project p
            INNER JOIN account_analytic_line timesheet
                    ON timesheet.project_id = p.id
            INNER JOIN hr_employee employee
                    ON timesheet.employee_id = employee.id
            CROSS JOIN generate_series(
                        %(today)s - '180 days'::interval,
                        %(today)s,
                        '30 days'::interval
                       ) gs
                 WHERE p.id = %(project_id)s
                   AND gs >= timesheet.date
                   AND gs - '30 days'::interval < timesheet.date
              GROUP BY timesheet.employee_id,
                       gs, employee.name
              ORDER BY gs DESC, employee.name ASC
        """
        self.env.cr.execute(query, {'project_id': project.id, 'today': today})
        results = self.env.cr.dictfetchall()
        activities = defaultdict(lambda: {
            'unit_amount': 0,
            'worked': False,
        })
        digits = not self.env.company._is_timesheet_hour_uom() and 2 or 0
        for result in results:
            if result['period'] == today:
                activities[result['employee_id']] = {
                    'name': result['name'],
                    'unit_amount': formatLang(self.env, project._convert_project_uom_to_timesheet_encode_uom(result['unit_amount']), digits=digits),
                    'worked': True,
                    'new': True,
                }
            else:
                name = activities[result['employee_id']].get('name', result['name'])
                activities[result['employee_id']].update(name=name, new=False)
        return list(activities.values())
