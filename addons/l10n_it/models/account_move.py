# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _message_set_main_attachment_id(self, attachments, force=False, filter_xml=True):
        if self.message_main_attachment_id.mimetype == "application/pkcs7-mime":
            force = True
        super()._message_set_main_attachment_id(attachments, force, filter_xml)
