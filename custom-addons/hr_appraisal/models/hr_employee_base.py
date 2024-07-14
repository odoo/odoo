# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"
    _description = "Basic Employee"

    parent_user_id = fields.Many2one(related='parent_id.user_id', string="Parent User")
    last_appraisal_id = fields.Many2one('hr.appraisal')

    def action_send_appraisal_request(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.appraisal',
            'name': 'Appraisal Request',
            'context': self.env.context,
        }

    def action_open_last_appraisal(self):
        self.ensure_one()
        return {
            'view_mode': 'form',
            'res_model': 'hr.appraisal',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.last_appraisal_id.id,
        }

    def _create_multi_appraisals(self):
        active_ids = self.env.context.get('active_ids')
        appraisals = self.env['hr.appraisal']

        if active_ids:
            create_vals = []
            date_close = datetime.date.today() + relativedelta(months=+1)
            for employee in self.env['hr.employee'].browse(active_ids):
                appraisal = employee.appraisal_ids.filtered(lambda a: a.date_close == date_close)
                if appraisal:
                    appraisals |= appraisal
                else:
                    create_vals.append({
                        'employee_id': employee.id,
                        'manager_ids': employee.parent_id,
                    })
            new_appraisals = self.env['hr.appraisal'].create(create_vals)
            appraisals = appraisals + new_appraisals

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,list,form',
            'res_model': 'hr.appraisal',
            'name': 'Appraisal Requests',
            'domain': [('id', 'in', appraisals.ids)],
            'context': self.env.context,
            'help': _("""<p class="o_view_nocontent_smiling_face">
                            Schedule an appraisal
                        </p><p>
                            Plan appraisals with your colleagues, collect and discuss feedback.
                        </p>""")
        }
