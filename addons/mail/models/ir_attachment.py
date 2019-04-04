# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.multi
    def _post_add_create(self):
        """ Overrides behaviour when the attachment is created through the controller
        """
        super(IrAttachment, self)._post_add_create()
        for record in self:
            record.register_as_main_attachment(force=False)

    @api.multi
    def unlink(self):
        self.remove_as_main_attachment()
        super(IrAttachment, self).unlink()

    @api.multi
    def remove_as_main_attachment(self):
        for attachment in self:
            related_record = self.env[attachment.res_model].browse(attachment.res_id)
            if related_record and hasattr(related_record, 'message_main_attachment_id'):
                if related_record.message_main_attachment_id == attachment:
                    related_record.message_main_attachment_id = False

    def register_as_main_attachment(self, force=True):
        """ Registers this attachment as the main one of the model it is
        attached to.
        """
        self.ensure_one()
        related_record = self.env[self.res_model].browse(self.res_id)
        # message_main_attachment_id field can be empty, that's why we compare to False;
        # we are just checking that it exists on the model before writing it
        if related_record and hasattr(related_record, 'message_main_attachment_id'):
            if force or not related_record.message_main_attachment_id:
                related_record.message_main_attachment_id = self
