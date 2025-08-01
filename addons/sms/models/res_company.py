from odoo import models

from odoo.addons.sms.tools.sms_api import SmsApi


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_sms_api_class(self):
        self.ensure_one()
        return SmsApi
