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

    def _store_init_global_fields(self, res: Store.FieldList):
        super()._store_init_global_fields(res)
        # sudo: ir.config_parameter - reading hard-coded keys to check their existence, safe to
        # return whether the features are enabled
        get_str = self.env["ir.config_parameter"].sudo().get_str
        res.attr("hasGifPickerFeature", bool(get_str("discuss.tenor_api_key")))
        res.attr("hasMessageTranslationFeature", bool(get_str("mail.google_translate_api_key")))
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
