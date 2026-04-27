from odoo import api, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    @api.model
    def _get_model_info_by_xmlid(self):
        info = super()._get_model_info_by_xmlid()
        info['hr_payroll_holidays.mail_activity_data_hr_leave_to_defer'] = {
            'res_model': 'hr.leave',
            'unlink': False,
        }
        return info
