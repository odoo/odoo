# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from dateutil.relativedelta import relativedelta


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    def _compute_plan_date(self):
        todo = self.filtered(lambda s: s.res_model == 'hr.employee')
        for scheduler in todo:
            selected_employees = scheduler._get_applied_on_records()
            start_dates = selected_employees.filtered('first_contract_date').mapped('first_contract_date')
            if start_dates:
                today = fields.Date.today()
                planned_due_date = min(start_dates)
                if planned_due_date < today or (planned_due_date - today).days < 30:
                    scheduler.plan_date = today + relativedelta(days=+30)
                else:
                    scheduler.plan_date = planned_due_date
        super(MailActivitySchedule, self - todo)._compute_plan_date()
