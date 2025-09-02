# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib

from odoo import _, models, fields, api
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import limited_field_access_token, verify_limited_field_access_token
from odoo.addons.mail.tools.discuss import Store


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    thumbnail = fields.Image()
    has_thumbnail = fields.Boolean(compute="_compute_has_thumbnail")

    @api.depends("thumbnail")
    def _compute_has_thumbnail(self):
        for attachment in self.with_context(bin_size=True):
            attachment.has_thumbnail = bool(attachment.thumbnail)

    def _has_attachments_ownership(self, attachment_tokens):
        """ Checks if the current user has ownership of all attachments in the recordset.
            Ownership is defined as either:
            - Having 'write' access to the attachment.
            - Providing a valid, scoped 'attachment_ownership' access token.

            :param list attachment_tokens: A list of access tokens
        """
        attachment_tokens = attachment_tokens or ([None] * len(self))
        if len(attachment_tokens) != len(self):
            raise UserError(_("An access token must be provided for each attachment."))

        def is_owned(attachment, token):
            if not attachment.exists():
                return False
            if attachment.sudo(False).has_access("write"):
                return True
            return token and verify_limited_field_access_token(
                attachment, "id", token, scope="attachment_ownership"
            )

        return all(is_owned(att, tok) for att, tok in zip(self, attachment_tokens, strict=True))

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

    def _get_store_ownership_fields(self):
        return [Store.Attr("ownership_token", lambda a: a._get_ownership_token())]

    def _to_store_defaults(self, target):
        return [
            "checksum",
            "create_date",
            "file_size",
            "has_thumbnail",
            "mimetype",
            "name",
            Store.Attr("raw_access_token", lambda a: a._get_raw_access_token()),
            "res_name",
            Store.One("thread", [], as_thread=True),
            Store.Attr("thumbnail_access_token", lambda a: a._get_thumbnail_token()),
            "type",
            "url",
        ]

    def _get_ownership_token(self):
        """ Returns a scoped limited access token that indicates ownership of the attachment when
            using _has_attachments_ownership. If verified by verify_limited_field_access_token,
            accessing the attachment bypasses the ACLs.

            :rtype: str
        """
        self.ensure_one()
        return limited_field_access_token(self, field_name="id", scope="attachment_ownership")

    def _get_thumbnail_token(self):
        self.ensure_one()
        return limited_field_access_token(self, "thumbnail", scope="binary")
