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
                channel_ids = self._get_self_pinned_channel_ids()
                if self.env.user._is_internal():
                    channel_ids += self._get_self_needaction_channel_ids()
                return Domain("channel_type", "=", "channel") & Domain("id", "in", channel_ids)
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
        match (tab_id, filter_id):
            case ("chat", "chat_unread"):
                return Domain("self_member_id.is_unread", "=", True)
            case ("chat", "chat_group"):
                return Domain("channel_type", "=", "group")
            case ("channel", "channel_unread"):
                return Domain("self_member_id.is_unread", "=", True)
            case ("channel", "channel_thread"):
                return Domain("parent_channel_id", "!=", False)
            case ("meeting", "meeting_today"):
                return self.env["discuss.channel"]._get_meeting_today_domain()
            case ("meeting", "meeting_unread"):
                return Domain("self_member_id.is_unread", "=", True)
            case ("meeting", "meeting_thread"):
                return Domain("parent_channel_id", "!=", False)
        return super()._get_menu_tab_filter_domain(tab_id, filter_id)

    def _get_menu_tab_priority_domain(self, tab_id):
        """Optional domain whose matching records are fetched first by the load more
        route."""
        if tab_id == "meeting":
            return self.env["discuss.channel"]._get_meeting_ongoing_domain()
        return

    def _get_self_pinned_channel_ids(self):
        """Ids of the channels pinned by the current user or guest."""
        if (channel_ids := self.env.context.get("self_pinned_channel_ids")) is None:
            members = self.env["discuss.channel.member"].search_fetch(
                [("is_self", "=", True), ("is_pinned", "=", True)],
                ["channel_id"],
            )
            channel_ids = tuple(members.channel_id.ids)
            request.update_context(self_pinned_channel_ids=channel_ids)
        return list(channel_ids)

    def _get_self_needaction_channel_ids(self):
        """Ids of the channels with messages needing the action of the current user."""
        if (channel_ids := self.env.context.get("self_needaction_channel_ids")) is None:
            groups = self.env["mail.message"]._read_group(
                [
                    ("model", "=", "discuss.channel"),
                    ("message_type", "!=", "user_notification"),
                    ("needaction", "=", True),
                ],
                ["res_id"],
            )
            channel_ids = tuple(res_id for [res_id] in groups)
            request.update_context(self_needaction_channel_ids=channel_ids)
        return list(channel_ids)

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
        important_domain = Domain("id", "in", self._get_self_pinned_channel_ids()) & Domain(
            "self_member_id",
            "any",
            [("is_unread", "=", True), ("mute_until_dt", "=", False)],
        )
        if self.env.user._is_internal():
            important_domain |= Domain("id", "in", self._get_self_needaction_channel_ids())
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
        filter_ids=None,
        exclude_ids=None,
        search_term=None,
    ):
        domain = self._get_menu_load_more_domain(tab_id, filter_ids, exclude_ids)
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
