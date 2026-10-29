# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain

from odoo.addons.mail.controllers.discuss.messaging_menu import DiscussMessagingMenuController


class LivechatMessagingMenuController(DiscussMessagingMenuController):
    def _get_menu_tab_domain(self, tab_id):
        if tab_id != "livechat":
            return super()._get_menu_tab_domain(tab_id)
        # sudo: discuss.channel.member - only the user's own members, for performance: the
        # channels are then searched with their access rules.
        pinned_channel_ids = self.env["discuss.channel.member"].sudo().search_fetch(
            [("is_self", "=", True), ("is_pinned", "=", True)],
        ).channel_id.ids
        domain = Domain(
            [("channel_type", "=", "livechat"), ("id", "in", pinned_channel_ids)],
        )
        if self.env.user.has_group("im_livechat.im_livechat_group_user"):
            domain |= Domain("livechat_status", "=", "need_help")
        return domain

    def _get_menu_tab_priority_domain(self, tab_id):
        """Fetch the operator's own livechats first."""
        if tab_id == "livechat":
            # sudo: discuss.channel.member - only the user's own members, for performance: the
            # channels are then searched with their access rules.
            pinned_channel_ids = self.env["discuss.channel.member"].sudo().search_fetch(
                [("is_self", "=", True), ("is_pinned", "=", True)],
            ).channel_id.ids
            return Domain("id", "in", pinned_channel_ids)
        return super()._get_menu_tab_priority_domain(tab_id)

    def _get_menu_tab_filter_domain(self, tab_id, filter_id):
        match (tab_id, filter_id):
            case ("livechat", "livechat_need_help"):
                return Domain("livechat_status", "=", "need_help")
            case ("livechat", "livechat_unread"):
                return Domain("self_member_id.is_unread", "=", True)
        return super()._get_menu_tab_filter_domain(tab_id, filter_id)
