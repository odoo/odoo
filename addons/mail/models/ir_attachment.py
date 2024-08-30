# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib

from odoo import _, models, SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.tools import consteq
from odoo.addons.mail.tools.discuss import Store


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

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
        super()._post_add_create(**kwargs)
        self.register_as_main_attachment(force=False)

    def register_as_main_attachment(self, force=True):
        """ Registers this attachment as the main one of the model it is
        attached to.

        :param bool force: if set, the method always updates the existing main attachment
            otherwise it only sets the main attachment if there is none.
        """
        todo = self.filtered(lambda a: a.res_model and a.res_id)
        if not todo:
            return

        for model, attachments in todo.grouped("res_model").items():
            related_records = self.env[model].browse(attachments.mapped("res_id"))
            if not hasattr(related_records, '_message_set_main_attachment_id'):
                return

            # this action is generic; if user cannot update record do not crash
            # just skip update
            for related_record, attachment in zip(related_records, attachments):
                with contextlib.suppress(AccessError):
                    related_record._message_set_main_attachment_id(attachment, force=force)

    def _delete_and_notify(self, message=None):
        if message:
            # sudo: mail.message - safe write just updating the date, because guests don't have the rights
            message.sudo().write({})  # to make sure write_date on the message is updated
        for attachment in self:
            attachment._bus_send(
                "ir.attachment/delete",
                {
                    "id": attachment.id,
                    "message": (
                        {"id": message.id, "write_date": message.write_date} if message else None
                    ),
                },
            )
        self.unlink()

    def _to_store(self, store: Store, /, *, fields=None, extra_fields=None):
        if fields is None:
            fields = [
                "checksum",
                "create_date",
                "filename",
                "mimetype",
                "name",
                "res_name",
                "size",
                "thread",
            ]
        if extra_fields:
            fields.extend(extra_fields)
        safari = (
            request
            and request.httprequest.user_agent
            and request.httprequest.user_agent.browser == "safari"
        )
        for attachment in self:
            data = attachment._read_format(
                [field for field in fields if field not in ["filename", "size", "thread"]],
                load=False,
            )[0]
            if "filename" in fields:
                data["filename"] = attachment.name
            if (
                "mimetype" in fields
                and safari
                and attachment.mimetype
                and "video" in attachment.mimetype
            ):
                data["mimetype"] = "application/octet-stream"
            if "size" in fields:
                data["size"] = attachment.file_size
            if "thread" in fields:
                data["thread"] = (
                    Store.one(
                        self.env[attachment.res_model].browse(attachment.res_id),
                        as_thread=True,
                        only_id=True,
                    )
                    if attachment.res_model != "mail.compose.message" and attachment.res_id
                    else False
                )
            store.add(attachment, data)
