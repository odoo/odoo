# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.http import request

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.store_handler import store_handler


class DiscussMessagingMenuController(WebclientController):
    def store_messaging_menu_initialize_counters(
        self,
        store: Store,
        domain_by_tab_id_by_record_type,
    ):
        super().store_messaging_menu_initialize_counters(
            store,
            domain_by_tab_id_by_record_type=domain_by_tab_id_by_record_type,
        )
        channel_domain_by_tab_id = domain_by_tab_id_by_record_type.get("discuss.channel")
        if not channel_domain_by_tab_id:
            return
        members = self.env["discuss.channel.member"].search_fetch(
            [
                ("is_self", "=", True),
                ("is_pinned", "=", True),
                ("channel_id.active", "=", True),
                ("mute_until_dt", "=", False),
            ],
        )
        unread_channels = members.filtered(
            lambda m: m.message_unread_counter or m.channel_id.message_needaction_counter,
        ).channel_id
        if self.env.user._is_internal():
            unread_channels |= self.env["discuss.channel"].search_fetch(
                [("message_needaction", "=", True), ("active", "=", True)],
            )
        for tab_id, domain in channel_domain_by_tab_id.items():
            store.add_model_values(
                "MessagingMenuTab",
                {"init_counter_ids": unread_channels.filtered_domain(domain).ids},
                id_data={"id": tab_id},
            )

    @store_handler("/mail/messaging_menu/discuss.channel/load_more", audience="everyone")
    def store_messaging_menu_discuss_channel_load_more(
        self,
        store: Store,
        domain,
        limit,
        search_term=None,
        priority_domain=None,
    ):
        full_domain = Domain(domain)
        if search_term:
            full_domain &= Domain("name", "ilike", search_term)
        # Favorites first, plus any tab specific priority (e.g. the agent's own livechats).
        priority = Domain("self_member_id.is_favorite", "=", True)
        if priority_domain:
            priority |= Domain(priority_domain)
        channels = self.env["discuss.channel"].search_fetch(
            full_domain & priority,
            limit=limit,
            order="last_interest_dt desc, id desc",
        )
        remaining = limit - len(channels)
        if remaining > 0:
            channels |= self.env["discuss.channel"].search_fetch(
                full_domain & Domain("id", "not in", channels.ids),
                limit=remaining,
                order="last_interest_dt desc, id desc",
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
            order="__count DESC",
            limit=3,
        )
        channels = self.env["discuss.channel"]
        for row in results:
            channels |= row[0]
        store.add_global_values(
            lambda res: res.many("most_popular_channels", "_store_channel_fields", value=channels),
        )
