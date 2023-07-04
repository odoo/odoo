# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.base.models.res_users import is_selection_groups


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        # Auto-subscribe to channels unless skip explicitly requested
        if not self.env.context.get("discuss_channel_nosubscribe"):
            self.env["discuss.channel"].search(
                [("group_ids", "in", users.groups_id.ids)]
            )._subscribe_users_automatically()
        return users

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals and not vals["active"]:
            self._unsubscribe_from_non_public_channels()
        sel_groups = [vals[k] for k in vals if is_selection_groups(k) and vals[k]]
        if vals.get("groups_id"):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals["groups_id"] if command[0] == 4]
            user_group_ids += [id for command in vals["groups_id"] if command[0] == 6 for id in command[2]]
            self.env["discuss.channel"].search([("group_ids", "in", user_group_ids)])._subscribe_users_automatically()
        elif sel_groups:
            self.env["discuss.channel"].search([("group_ids", "in", sel_groups)])._subscribe_users_automatically()
        return res

    def unlink(self):
        self._unsubscribe_from_non_public_channels()
        return super().unlink()

    def _unsubscribe_from_non_public_channels(self):
        """This method un-subscribes users from group restricted channels. Main purpose
        of this method is to prevent sending internal communication to archived / deleted users.
        We do not un-subscribes users from public channels because in most common cases,
        public channels are mailing list (e-mail based) and so users should always receive
        updates from public channels until they manually un-subscribe themselves.
        """
        domain = [("partner_id", "in", self.partner_id.ids)]
        current_cm = self.env["discuss.channel.member"].sudo().search(domain)
        current_cm.filtered(
            lambda cm: (cm.channel_id.channel_type == "channel" and cm.channel_id.group_public_id)
        ).unlink()

    def _init_messaging(self):
        self.ensure_one()
        return {
            'channels': self.partner_id._get_channels_as_member()._channel_info(),
            'hasGifPickerFeature': bool(self.env["ir.config_parameter"].sudo().get_param("discuss.tenor_api_key")),
            **super()._init_messaging(),
        }
