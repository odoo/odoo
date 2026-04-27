# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    def _plan_filter_activity_templates_to_schedule(self):
        if self.res_model != 'hr.employee':
            return super()._plan_filter_activity_templates_to_schedule()
        return self.plan_id.template_ids.filtered(lambda a: not a.is_signature_request or a.responsible_count > 2)

    def action_schedule_plan(self):
        res = super().action_schedule_plan()
        if self.res_model != 'hr.employee':
            return res

        for employee in self._get_applied_on_records():
            for signature_request in self.plan_id.template_ids - self._plan_filter_activity_templates_to_schedule():
                employee_role = signature_request.employee_role_id
                responsible = signature_request._determine_responsible(self.plan_on_demand_user_id, employee)['responsible']

                self.env['hr.contract.sign.document.wizard'].create({
                    'contract_id': employee.contract_id.id,
                    'employee_ids': [(4, employee.id)],
                    'responsible_id': responsible.id,
                    'employee_role_id': employee_role and employee_role.id,
                    'sign_template_ids': [(4, signature_request.sign_template_id.id)],
                    'subject': _('Signature Request'),
                }).validate_signature()

        return res
