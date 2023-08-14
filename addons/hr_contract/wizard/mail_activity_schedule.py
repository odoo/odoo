# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    @api.model
    def default_get(self, field_list):
        result = super().default_get(field_list)
        model = self._get_default_res_model()
        res_ids = self._get_default_res_ids()
        if not ('date_plan_deadline' in field_list and model == 'hr.employee' and res_ids):
            return result
        selected_employees = self.env['hr.employee'].browse(self._get_converted_res_ids(res_ids))
        start_dates = selected_employees.filtered('first_contract_date').mapped('first_contract_date')
        if start_dates:
            today = fields.Date.today()
            planned_due_date = start_dates[0] if len(set(start_dates)) == len(selected_employees) else min(start_dates)

            if planned_due_date < today:
                result['date_plan_deadline'] = today + relativedelta(days=+30)
            else:
                if (planned_due_date-today).days < 30:
                    result['date_plan_deadline'] = today + relativedelta(days=+30)
                else:
                    result['date_plan_deadline'] = planned_due_date

        return result
