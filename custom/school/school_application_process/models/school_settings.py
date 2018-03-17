from odoo import models, fields, api


class SchoolSettings(models.TransientModel):
    _inherit = 'school.settings'
    send_application_sms = fields.Boolean(string='Send Application SMS Notification',
                                          default=False)

    @api.model
    def get_default_company_values(self, fields):
        company = self.env.user.company_id
        return {
            'send_application_sms': company.send_application_sms,
        }

    @api.one
    def set_company_values(self):
        company = self.env.user.company_id
        company.send_application_sms = self.send_application_sms
