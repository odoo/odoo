# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.exceptions import UserError


class MailMessage(models.Model):
    _inherit = 'mail.message'

    message_type = fields.Selection(
        selection_add=[('whatsapp_message', 'WhatsApp')],
        ondelete={'whatsapp_message': lambda recs: recs.write({'message_type': 'comment'})},
    )
    wa_message_ids = fields.One2many('whatsapp.message', 'mail_message_id', string='Related WhatsApp Messages')

    def _message_reaction(self, content, action, partner, guest, store: Store = None):
        if self.message_type == "whatsapp_message" and self.wa_message_ids:
            if action == "add":
                # Only allow one emoji, remove any existing one first
                previous_reaction = self.env["mail.message.reaction"].search([
                    ("message_id", "=", self.id),
                    ("partner_id", "=", partner.id),
                    ("guest_id", "=", guest.id),
                ], limit=1)
                if previous_reaction:
                    # If the same reaction already exists, do nothing
                    previous_reaction_emoji = previous_reaction.content
                    if previous_reaction_emoji == content:
                        return
                    previous_reaction.unlink()
                    self._bus_send_reaction_group(previous_reaction_emoji)

            wa_msg = self.wa_message_ids[0]
            wa_api = WhatsAppApi(wa_msg.wa_account_id)
            send_vals = {
                "message_id": wa_msg.msg_uid,
                "emoji": content if action == "add" else ""
            }
            try:
                wa_api._send_whatsapp(wa_msg.mobile_number, message_type="reaction", send_vals=send_vals)
            except WhatsAppError as e:
                raise UserError(str(e))

        super()._message_reaction(content, action, partner, guest, store)

    def _post_whatsapp_reaction(self, reaction_content, partner_id):
        self.ensure_one()
        reaction_to_delete = self.reaction_ids.filtered(lambda r: r.partner_id == partner_id)
        if reaction_to_delete:
            content = reaction_to_delete.content
            reaction_to_delete.unlink()
            self._bus_send_reaction_group(content)
        if reaction_content and self.id:
            self.env['mail.message.reaction'].create({
                'message_id': self.id,
                'content': reaction_content,
                'partner_id': partner_id.id,
            })
            self._bus_send_reaction_group(reaction_content)

    def _to_store(self, store: Store, **kwargs):
        super()._to_store(store, **kwargs)
        if whatsapp_mail_messages := self.filtered(lambda m: m.message_type == "whatsapp_message"):
            for whatsapp_message in (
                self.env["whatsapp.message"]
                .sudo()
                .search([("mail_message_id", "in", whatsapp_mail_messages.ids)])
            ):
                store.add(
                    whatsapp_message.mail_message_id, {"whatsappStatus": whatsapp_message.state}
                )
