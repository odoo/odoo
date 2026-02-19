# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    is_in_call = fields.Boolean("Is in call", related="partner_id.is_in_call")

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._auto_subscribe_channels()
        return users

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals and not vals["active"]:
            self._unsubscribe_from_non_public_channels()
        if vals.get("group_ids") or vals.get("company_id"):
            self._auto_subscribe_channels()
        return res

    def unlink(self):
        self._unsubscribe_from_non_public_channels()
        return super().unlink()

    def _auto_subscribe_channels(self):
        users = self.filtered(lambda u: u.partner_id.active)
        if not users:
            return
        channels = self.env["discuss.channel"].search([
                ("auto_join", "=", True),
                *users._get_auto_subscribe_domain(),
            ])
        for user in users:
            filtered_channels = channels.filtered_domain([
                *user._get_auto_subscribe_domain(),
                ("id", "not in", user.partner_id.channel_ids.ids),
                ("auto_joined_partner_ids", "not in", user.partner_id.id),
            ])
            members_to_create = dict.fromkeys(filtered_channels.ids, user.partner_id.ids)
            if members_to_create:
                filtered_channels._subscribe_users_automatically(members_to_create)

    def _get_auto_subscribe_domain(self):
        return [
            ("group_public_id", "in", [False] + self.group_ids.all_implied_ids.ids),
            ("company_ids", "in", [False] + self.sudo().company_ids.ids),
            ("group_ids", "in", [False] + self.group_ids.all_implied_ids.ids),
        ]

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

    def _store_init_global_fields(self, res: Store.FieldList):
        super()._store_init_global_fields(res)
        # sudo: ir.config_parameter - reading hard-coded config params to check their existence, safe to
        # return whether the features are enabled
        get_bool = self.env["ir.config_parameter"].sudo().get_bool
        res.attr("hasGifPickerFeature", get_bool("discuss.use_tenor_api"))
        res.attr("hasMessageTranslationFeature", get_bool("mail.use_google_translate_api"))
        res.attr(
            "hasCannedResponses",
            self.env["mail.canned.response"].sudo().search_count(
                Domain("create_uid", "=", self.id)
                | Domain("group_ids", "in", self.all_group_ids.ids),
                limit=1,
            ) > 0,
        )
        res.attr(
            "channel_types_with_seen_infos",
            sorted(self.env["discuss.channel"]._types_allowing_seen_infos()),
        )
