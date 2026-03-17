from odoo import api, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    @api.model
    def _get_model_info_by_xmlid(self):
        info = super()._get_model_info_by_xmlid()
        info['hr_time.mail_act_leave_approval'] = {'res_model': 'hr.time', 'unlink': False}
        info['hr_time.mail_act_leave_second_approval'] = {'res_model': 'hr.time', 'unlink': False}
        info['hr_time.mail_act_leave_allocation_approval'] = {'res_model': 'hr.time.allocation', 'unlink': False}
        info['hr_time.mail_act_leave_allocation_second_approval'] = {'res_model': 'hr.time.allocation', 'unlink': False}
        return info
