# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib

from odoo import _, models, SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError, UserError
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
        self._notify_thread_attachment(unlink=False)

    def _notify_thread_attachment(self, unlink=True, message=None):
        supported_records = self.filtered(lambda a: a.res_model and a.res_id)
        if not supported_records:
            return
        if message:
            store = Store(
                message,
                {
                    "attachment_ids": Store.Many(
                        self,
                        mode="DELETE" if unlink else "ADD",
                    ),
                }
            )
            store.delete(self)
            if hasattr(message._bus_channel(), "_get_message_sub_channel"):
                message._bus_send_store(store, subchannel=message._bus_channel()._get_message_sub_channel(message))
            else:
                message._bus_send_store(store, subchannel=message._get_thread_bus_subchannel())
        else:
            for model, attachments in supported_records.grouped("res_model").items():
                threads = self.env[model].search([("id", "in", attachments.mapped("res_id"))])
                if not threads:
                    continue
                for thread in threads:
                    store = Store(
                        thread,
                        {
                            "attachments": Store.Many(
                                attachments.filtered(lambda a: a.res_id == thread.id),
                                mode="DELETE" if unlink else "ADD",
                            )
                        },
                        as_thread=True,
                    )
                    store.delete(attachments)
                    thread._bus_send_store(store, subchannel="thread")

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
        self._notify_thread_attachment(unlink=True, message=message)
        self.unlink()

    def _to_store_defaults(self):
        return [
            "checksum",
            "create_date",
            "file_size",
            "mimetype",
            "name",
            Store.Attr("raw_access_token", lambda a: a._get_raw_access_token()),
            "res_name",
            Store.One("thread", [], as_thread=True),
            "type",
            "url",
        ]
