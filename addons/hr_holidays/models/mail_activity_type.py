from odoo import api, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    @api.model
    def _get_model_info_by_xmlid(self):
        info = super()._get_model_info_by_xmlid()
        info['hr_holidays.mail_act_leave_approval'] = {'res_model': 'hr.leave', 'unlink': False}
        info['hr_holidays.mail_act_leave_second_approval'] = {'res_model': 'hr.leave', 'unlink': False}
        info['hr_holidays.mail_act_leave_allocation_approval'] = {'res_model': 'hr.leave.allocation', 'unlink': False}
        return info
