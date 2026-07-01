import base64
from odoo import api, fields, models
from odoo.exceptions import UserError

ODOO_CHANNEL_TYPES = ["chat", "channel", "livechat", "group"]


class MailChannel(models.Model):
    _inherit = "mail.channel"

    is_pinned = fields.Boolean(
        "Visible for me",
        compute="_compute_is_pinned",
        inverse="_inverse_is_pinned",
        help="Refresh page after updating",
    )

    @api.model
    def _prepare_multi_livechat_channel_vals(
            self, channel_type, channel_name, partner_ids, avatar
    ):
        return {
            "channel_partner_ids": [(4, pid) for pid in partner_ids],
            "group_public_id": None,
            "channel_type": channel_type,
            "name": channel_name,
        }

    def _compute_is_pinned(self):
        # TODO: make batch search via read_group
        for r in self:
            r.is_pinned = self.env["mail.channel.member"].search_count(
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("channel_id", "=", r.id),
                    ("is_pinned", "=", True),
                ]
            )

    def _inverse_is_pinned(self):
        # TODO: make batch search via read_group
        for r in self:
            channel_partner = self.env["mail.channel.member"].search(
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("channel_id", "=", r.id),
                ]
            )
            # TODO: can channel_partner be empty or more than 1 record?
            channel_partner.is_pinned = r.is_pinned

    def _compute_is_chat(self):
        super(MailChannel, self)._compute_is_chat()
        for record in self:
            if record.channel_type not in ODOO_CHANNEL_TYPES:
                record.is_chat = True

    @api.model
    def multi_livechat_info(self):
        field = self.env["mail.channel"]._fields["channel_type"]
        return {
            "channel_types": {
                key: value
                for key, value in field.selection
                if key not in ODOO_CHANNEL_TYPES
            }
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_forbid(self):
        for record in self:
            if record.channel_type not in ODOO_CHANNEL_TYPES:
                raise UserError('Channel cannot be deleted, only archived')

    def action_archive(self):
        link = self.env['us.messenger.link'].sudo().search(
            [('model', '=', 'mail.channel'), ('ref2', '=', self.ids), ('active', '=', True)])
        link.action_archive()
        return super(MailChannel, self).action_archive()

    def action_unarchive(self):
        link = self.env['us.messenger.link'].sudo().search(
            [('model', '=', 'mail.channel'), ('ref2', '=', self.ids), ('active', '=', False)])
        link.action_unarchive()
        return super(MailChannel, self).action_unarchive()
