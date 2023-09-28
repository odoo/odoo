# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    @api.depends('res_model_id', 'res_ids')
    def _compute_date_plan_deadline(self):
        for wizard in self:
            if wizard.res_model != 'hr.employee':
                continue
            selected_employees = wizard._get_applied_on_records()
            start_dates = selected_employees.filtered('first_contract_date').mapped('first_contract_date')
            if start_dates:
                today = fields.Date.today()
                planned_due_date = min(start_dates)

                if planned_due_date < today or (planned_due_date - today).days < 30:
                    wizard.date_plan_deadline = today + relativedelta(days=+30)
                else:
                    wizard.date_plan_deadline = planned_due_date
