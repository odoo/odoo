# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    is_in_call = fields.Boolean("Is in call", related="partner_id.is_in_call")

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        self.env["discuss.channel"].search([("group_ids", "in", users.all_group_ids.ids)])._subscribe_users_automatically()
        return users

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals and not vals["active"]:
            self._unsubscribe_from_non_public_channels()
        if vals.get("group_ids"):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals["group_ids"] if command[0] == 4]
            user_group_ids += [id for command in vals["group_ids"] if command[0] == 6 for id in command[2]]
            user_group_ids += self.env['res.groups'].browse(user_group_ids).all_implied_ids._ids
            self.env["discuss.channel"].search([("group_ids", "in", user_group_ids)])._subscribe_users_automatically()
        return res

    def unlink(self):
        self._unsubscribe_from_non_public_channels()
        return super().unlink()

    def _unsubscribe_from_non_public_channels(self):
        """This method un-subscribes users from group restricted channels. Main purpose
        of this method is to prevent sending internal communication to archived / deleted users.
        """
        domain = [("partner_id", "in", self.partner_id.ids)]
        # sudo: discuss.channel.member - removing member of other users based on channel restrictions
        current_cm = self.env["discuss.channel.member"].sudo().search(domain)
        current_cm.filtered(
            lambda cm: (cm.channel_id.channel_type == "channel" and cm.channel_id.group_public_id)
        ).unlink()

    def _init_messaging(self, store: Store):
        self = self.with_user(self)
        channels = self.env["discuss.channel"]._get_channels_as_member()
        domain = [("channel_id", "in", channels.ids), ("is_self", "=", True)]
        members = self.env["discuss.channel.member"].search(domain)
        members_with_unread = members.filtered(lambda member: member.message_unread_counter)
        # fetch channels data before calling super to benefit from prefetching (channel info might
        # prefetch a lot of data that super could use, about the current user in particular)
        super()._init_messaging(store)
        store.add_global_values(initChannelsUnreadCounter=len(members_with_unread))

    def _init_store_data(self, store: Store):
        super()._init_store_data(store)
        # sudo: ir.config_parameter - reading hard-coded keys to check their existence, safe to
        # return whether the features are enabled
        get_param = self.env["ir.config_parameter"].sudo().get_param
        store.add_global_values(
            hasGifPickerFeature=bool(get_param("discuss.tenor_api_key")),
            hasMessageTranslationFeature=bool(get_param("mail.google_translate_api_key")),
            hasCannedResponses=bool(self.env["mail.canned.response"].sudo().search([
                "|",
                ("create_uid", "=", self.env.user.id),
                ("group_ids", "in", self.env.user.all_group_ids.ids),
            ], limit=1)) if self.env.user else False,
            channel_types_with_seen_infos=sorted(
                self.env["discuss.channel"]._types_allowing_seen_infos()
            ),
        )
