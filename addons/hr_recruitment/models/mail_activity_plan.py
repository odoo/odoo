# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import mail

from odoo import models


class MailActivityPlan(models.Model, mail.MailActivityPlan):

    def _compute_department_assignable(self):
        super()._compute_department_assignable()
        for plan in self:
            if not plan.department_assignable:
                plan.department_assignable = plan.res_model == 'hr.applicant'
