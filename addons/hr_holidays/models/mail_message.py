# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _author_to_store_partner_fields(self):
        return super()._author_to_store_partner_fields() + ["im_status", "leave_date_to"]
