# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain

from odoo.addons.mail.controllers.discuss.messaging_menu import DiscussMessagingMenuController


class LivechatMessagingMenuController(DiscussMessagingMenuController):
    def _get_menu_tab_domain(self, tab_id):
        if tab_id != "livechat":
            return super()._get_menu_tab_domain(tab_id)
        domain = Domain(
            [("channel_type", "=", "livechat"), ("self_member_id.is_pinned", "=", True)],
        )
        if self.env.user.has_group("im_livechat.im_livechat_group_user"):
            domain |= Domain("livechat_status", "=", "need_help")
        return domain

    def _get_menu_tab_priority_domain(self, tab_id):
        """Fetch the operator's own livechats first."""
        if tab_id == "livechat":
            return Domain("self_member_id.is_pinned", "=", True)
        return super()._get_menu_tab_priority_domain(tab_id)

    def _get_menu_tab_filter_domain(self, tab_id, filter_id):
        if tab_id == "livechat" and filter_id == "livechat_need_help":
            return Domain("livechat_status", "=", "need_help")
        return super()._get_menu_tab_filter_domain(tab_id, filter_id)
