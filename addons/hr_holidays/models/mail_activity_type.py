from odoo import api, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    @api.model
    def _get_xmlid_model_link(self):
        link = super()._get_xmlid_model_link()
        link['hr_holidays.mail_act_leave_approval'] = 'hr.leave'
        link['hr_holidays.mail_act_leave_second_approval'] = 'hr.leave'
        link['hr_holidays.mail_act_leave_allocation_approval'] = 'hr.leave.allocation'
        return link
