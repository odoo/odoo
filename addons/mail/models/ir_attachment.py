# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import AccessError

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _post_add_create(self):
        """ Overrides behaviour when the attachment is created through the controller
        """
        super(IrAttachment, self)._post_add_create()
        for record in self:
            record.register_as_main_attachment(force=False)

    def register_as_main_attachment(self, force=True):
        """ Registers this attachment as the main one of the model it is
        attached to.
        """
        self.ensure_one()
        if not self.res_model:
            return
        related_record = self.env[self.res_model].browse(self.res_id)
        if not related_record.check_access_rights('write', raise_exception=False):
            return
        # message_main_attachment_id field can be empty, that's why we compare to False;
        # we are just checking that it exists on the model before writing it
        if related_record and hasattr(related_record, 'message_main_attachment_id'):
            if force or not related_record.message_main_attachment_id:
                #Ignore AccessError, if you don't have access to modify the document
                #Just don't set the value
                try:
                    related_record.message_main_attachment_id = self
                except AccessError:
                    pass
