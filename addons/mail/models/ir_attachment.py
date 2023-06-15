# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib

from odoo import api, models
from odoo.exceptions import AccessError
from odoo.http import request


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

        :param bool force: if set, the method always updates the existing main attachment
            otherwise it only sets the main attachment if there is none.
        """
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return
        related_record = self.env[self.res_model].browse(self.res_id)
        if not related_record or \
                not related_record.check_access_rights('write', raise_exception=False) or \
                not hasattr(related_record, 'message_main_attachment_id'):
            return

        if force or not related_record.message_main_attachment_id:
            with contextlib.suppress(AccessError):
                related_record.message_main_attachment_id = self

    def _delete_and_notify(self, message=None):
        if message:
            message.write({})  # to make sure write_date on the message is updated
        self.env['bus.bus']._sendmany((attachment._bus_notification_target(), 'ir.attachment/delete', {
            'id': attachment.id, 'message': {'id': message.id, 'write_date': message.write_date} if message else None
        }) for attachment in self)
        self.unlink()

    def _bus_notification_target(self):
        self.ensure_one()
        return self.env.user.partner_id

    def _attachment_format(self):
        safari = request and request.httprequest.user_agent and request.httprequest.user_agent.browser == 'safari'
        return [
            {
                'checksum': attachment.checksum,
                'id': attachment.id,
                'filename': attachment.name,
                'name': attachment.name,
                'mimetype': 'application/octet-stream' if safari and attachment.mimetype and 'video' in attachment.mimetype else attachment.mimetype,
                'originThread': [('insert', {
                    'id': attachment.res_id,
                    'model': attachment.res_model,
                })],
            }
            for attachment in self
        ]

    @api.model
    def _get_upload_env(self, request, thread_model, thread_id):
        return request.env
