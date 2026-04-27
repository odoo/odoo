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
    last_appraisal_state = fields.Selection(related='last_appraisal_id.state')

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
        employee_appraisals = self.with_context(active_test=False).appraisal_ids
        opened_appraisals = employee_appraisals.filtered(lambda a: a.state in ['new', 'pending'])
        done_appraisals = employee_appraisals.filtered(lambda a: a.state == 'done')
        relevant_appraisals = employee_appraisals
        if opened_appraisals:
            relevant_appraisals = opened_appraisals
        elif done_appraisals:
            relevant_appraisals = done_appraisals[0]
        if len(relevant_appraisals) == 1:
            return {
                'view_mode': 'form',
                'res_model': 'hr.appraisal',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': relevant_appraisals.id,
            }
        else:
            return {
                'view_mode': 'list',
                'name': _('New and Pending Appraisals'),
                'res_model': 'hr.appraisal',
                "views": [[self.env.ref('hr_appraisal.view_hr_appraisal_tree').id, "list"], [False, "form"]],
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', 'in', relevant_appraisals.ids)],
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

    def _compute_can_request_appraisal(self):
        children_ids = self.env.user.get_employee_autocomplete_ids().ids
        for employee in self.sudo():
            # Since this function is used in both private and public employees, to check if an employee is in the list
            # we need to check by their id, which is the same in corresponding private and public employees.
            employee.can_request_appraisal = employee.id in children_ids
