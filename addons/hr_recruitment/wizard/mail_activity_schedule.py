# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import calendar, hr


class MailActivitySchedule(hr.MailActivitySchedule, calendar.MailActivitySchedule):

    def _compute_plan_department_filterable(self):
        super()._compute_plan_department_filterable()
        for wizard in self:
            if not wizard.plan_department_filterable:
                wizard.plan_department_filterable = wizard.res_model == 'hr.applicant'
