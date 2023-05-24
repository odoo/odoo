# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta


class HrPlanWizard(models.TransientModel):
    _inherit = 'hr.plan.wizard'

    @api.model
    def default_get(self, field_list=None):
        result = super(HrPlanWizard, self).default_get(field_list)
        selected_employees = self.env['hr.employee'].browse(self.env.context['active_ids'])
        start_dates = selected_employees.filtered('first_contract_date').mapped('first_contract_date')
        if start_dates:
            today = fields.Date.today()
            planned_due_date = start_dates[0] if len(set(start_dates)) == len(selected_employees) else min(start_dates)

            if planned_due_date < today:
                result['due_date'] = today + relativedelta(days=+30)
            else:
                if (planned_due_date-today).days < 30:
                    result['due_date'] = today + relativedelta(days=+30)
                else:
                    result['due_date'] = planned_due_date

        return result
