# -*- coding: utf-8 -*-

from odoo import api, models


class PlannerHrLeave(models.Model):
    """This class is used to activate web.planner feature in 'hr_leave_request_aliasing' module"""

    _inherit = 'web.planner'

    @api.model
    def _get_planner_application(self):
        planner = super(PlannerHrLeave, self)._get_planner_application()
        planner.append(['planner_hr_leave', 'Leave Planner'])
        return planner

    @api.model
    def _prepare_planner_hr_leave_data(self):
        alias_record = self.env.ref('hr_leave_request_aliasing.mail_alias_leave')
        return {
            'alias_domain': alias_record.alias_domain,
            'alias_name': alias_record.alias_name,
        }

