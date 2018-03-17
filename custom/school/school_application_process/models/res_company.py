from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'
    send_application_sms = fields.Boolean(string='Send Application SMS Notification',
                                          default=False)