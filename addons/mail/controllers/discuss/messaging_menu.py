# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.http import request

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.store_handler import store_handler


class DiscussMessagingMenuController(WebclientController):
    def _get_menu_tab_domain(self, tab_id):
        match tab_id:
            case "notification":
                return super()._get_menu_tab_domain(tab_id) & Domain(
                    "model",
                    "!=",
                    "discuss.channel",
                )
            case "chat":
                return Domain(
                    [
                        ("channel_type", "in", ["chat", "group"]),
                        ("default_display_mode", "!=", "video_full_screen"),
                        ("self_member_id.is_pinned", "=", True),
                    ],
                )
            case "channel":
                channel_domain = Domain("self_member_id.is_pinned", "=", True)
                if self.env.user._is_internal():
                    channel_domain |= Domain("message_needaction", "=", True)
                return Domain("channel_type", "=", "channel") & channel_domain
            case "meeting":
                is_video_full_screen = Domain(
                    "default_display_mode",
                    "=",
                    "video_full_screen",
                ) | Domain("parent_channel_id.default_display_mode", "=", "video_full_screen")
                return (
                    Domain("channel_type", "=", "group")
                    & Domain("self_member_id.is_pinned", "=", True)
                    & is_video_full_screen
                )
            case _:
                return super()._get_menu_tab_domain(tab_id)

    def _get_menu_tab_filter_domain(self, tab_id, filter_id):
        if tab_id == "chat" and filter_id == "chat_unread":
            return Domain("self_member_id.is_unread", "=", True)
        return super()._get_menu_tab_filter_domain(tab_id, filter_id)

    def _get_menu_tab_priority_domain(self, tab_id):
        """Optional domain whose matching records are fetched first by the load more
        route."""
        return

    def store_messaging_menu_initialize_counters(
        self,
        store: Store,
        filter_id_by_tab_id_by_record_type,
    ):
        super().store_messaging_menu_initialize_counters(
            store,
            filter_id_by_tab_id_by_record_type=filter_id_by_tab_id_by_record_type,
        )
        filter_id_by_tab_id = filter_id_by_tab_id_by_record_type.get("discuss.channel")
        if not filter_id_by_tab_id:
            return
        important_domain = Domain(
            "channel_member_ids",
            "any",
            [
                ("is_pinned", "=", True),
                ("is_self", "=", True),
                ("is_unread", "=", True),
                ("mute_until_dt", "=", False),
            ],
        )
        if self.env.user._is_internal():
            important_domain |= Domain("message_needaction", "=", True)
        important_channels = self.env["discuss.channel"].search_fetch(
            Domain("active", "=", True) & important_domain,
        )
        domain_by_tab_id = self.get_menu_counter_domain_by_tab_id(filter_id_by_tab_id)
        self._add_menu_tab_counters_to_store(store, important_channels, domain_by_tab_id)

    @store_handler("/mail/messaging_menu/discuss.channel/load_more", audience="everyone")
    def store_messaging_menu_discuss_channel_load_more(
        self,
        store: Store,
        tab_id,
        limit,
        filter_id=None,
        exclude_ids=None,
        search_term=None,
    ):
        domain = self._get_menu_load_more_domain(tab_id, filter_id, exclude_ids)
        if search_term:
            domain &= Domain("name", "ilike", search_term)
        # Favorites first, plus any tab specific priority.
        priority_domain = Domain("self_member_id.is_favorite", "=", True)
        if priority_extra_domain := self._get_menu_tab_priority_domain(tab_id):
            priority_domain |= priority_extra_domain
        channels = self.env["discuss.channel"].search_fetch(
            domain & priority_domain,
            limit=limit,
            order="last_interest_dt DESC, id DESC",
        )
        remaining = limit - len(channels)
        if remaining > 0:
            channels |= self.env["discuss.channel"].search_fetch(
                domain & Domain("id", "not in", channels.ids),
                limit=remaining,
                order="last_interest_dt DESC, id DESC",
            )
        request.update_context(
            channels=self.env.context["channels"] | channels,
            add_channels_last_message=True,
            add_channels_last_needaction=True,
        )
        store.resolve_data_request(
            lambda res: res.attr("is_fully_loaded", len(channels) < limit),
        )

    @store_handler("/mail/messaging_menu/get_most_popular_channels", audience="everyone")
    def store_messaging_menu_get_most_popular_channels(self, store: Store):
        results = self.env["discuss.channel.member"]._read_group(
            domain=[("channel_id.channel_type", "=", "channel")],
            groupby=["channel_id"],
            aggregates=[],
            order="__count DESC, channel_id DESC",
            limit=3,
        )
        channels = self.env["discuss.channel"].browse([r[0].id for r in results])
        request.update_context(channels=self.env.context["channels"] | channels)
        store.add_global_values(
            lambda res: res.many("most_popular_channels", [], value=channels.ids),
        )
