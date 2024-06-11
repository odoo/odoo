# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib

from odoo import _, api, models, SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.tools import consteq


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def check(self, mode, values=None):
        super().check(mode, values=values)
        if mode == 'write' and not {'datas', 'db_datas', 'raw'} & (values or {}).keys():
            return True
        if mode not in ('unlink', 'write') or not self or self.env.is_admin():
            return True
        if self.create_uid == self.env.user:
            return True
        linked_messages = self.env['mail.message'].sudo().search([('attachment_ids', 'in', self.ids)])
        if not linked_messages:
            return True
        authors = linked_messages.author_id
        if len(authors) > 1 or authors != self.env.user.partner_id:
            raise AccessError(_("You may not unlink or modify the content of attachments from other people's messages"))

    def _check_attachments_access(self, attachment_tokens):
        """This method relies on access rules/rights and therefore it should not be called from a sudo env."""
        self = self.sudo(False)
        attachment_tokens = attachment_tokens or ([None] * len(self))
        if len(attachment_tokens) != len(self):
            raise UserError(_("An access token must be provided for each attachment."))
        for attachment, access_token in zip(self, attachment_tokens):
            try:
                attachment_sudo = attachment.with_user(SUPERUSER_ID).exists()
                if not attachment_sudo:
                    raise MissingError(_("The attachment %s does not exist.", attachment.id))
                try:
                    attachment.check('write')
                except AccessError:
                    if not access_token or not attachment_sudo.access_token or not consteq(attachment_sudo.access_token, access_token):
                        message_sudo = self.env['mail.message'].sudo().search([('attachment_ids', 'in', attachment_sudo.ids)], limit=1)
                        if not message_sudo or not message_sudo.is_current_user_or_guest_author:
                            raise
            except (AccessError, MissingError):
                raise UserError(_("The attachment %s does not exist or you do not have the rights to access it.", attachment.id))

    def _post_add_create(self, **kwargs):
        """ Overrides behaviour when the attachment is created through the controller
        """
        super(IrAttachment, self)._post_add_create(**kwargs)
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
            # sudo: mail.message - safe write just updating the date, because guests don't have the rights
            message.sudo().write({})  # to make sure write_date on the message is updated
        self.env['bus.bus']._sendmany((attachment._bus_notification_target(), 'ir.attachment/delete', {
            'id': attachment.id, 'message': {'id': message.id, 'write_date': message.write_date} if message else None
        }) for attachment in self)
        self.unlink()

    def _bus_notification_target(self):
        self.ensure_one()
        return self.env.user.partner_id

    def _attachment_format(self):
        safari = request and request.httprequest.user_agent and request.httprequest.user_agent.browser == 'safari'
        return [{
            'checksum': attachment.checksum,
            'create_date': attachment.create_date,
            'id': attachment.id,
            'filename': attachment.name,
            'name': attachment.name,
            "size": attachment.file_size,
            'res_name': attachment.res_name,
            'mimetype': 'application/octet-stream' if safari and attachment.mimetype and 'video' in attachment.mimetype else attachment.mimetype,
            'originThread': [('ADD', {
                'id': attachment.res_id,
                'model': attachment.res_model,
            })],
        } for attachment in self]
