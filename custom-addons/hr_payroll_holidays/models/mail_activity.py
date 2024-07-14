# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=None):
        leave_activities = self.filtered(lambda act: act.res_model == 'hr.leave' and act.res_id)
        if leave_activities:
            type_to_defer_id = self.env['ir.model.data']._xmlid_to_res_id(
                'hr_payroll_holidays.mail_activity_data_hr_leave_to_defer',
                raise_if_not_found=False
            )
            if type_to_defer_id:
                leave_activities = leave_activities.filtered(lambda act: act.activity_type_id.id == type_to_defer_id)
        if leave_activities:
            self.env['hr.leave'].browse(leave_activities.mapped('res_id')).write({'payslip_state': 'done'})  # done or normal??? to check
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
