import { _resolve_messages } from "@mail/../tests/mock_server/mail_mock_server";
import { registerStoreHandler } from "@mail/../tests/mock_server/store_handler";

import { makeKwArgs } from "@web/../tests/web_test_helpers";

// Mirrors the store handlers of `mail/controllers/messaging_menu.py` (MessagingMenuController)
// and `mail/controllers/discuss/messaging_menu.py` (DiscussMessagingMenuController) — both live
// in the `mail` addon, so their tabs are registered together here directly (no `patch()` needed
// within the same addon). Other addons (im_livechat, whatsapp, ai) extend `messagingMenuHelpers`
// with `patch(messagingMenuHelpers, {...})`, calling `super()` to fall through, mirroring how
// their own Python controllers subclass `DiscussMessagingMenuController`.

/**
 * Mirrors `MessagingMenuController`'s / `DiscussMessagingMenuController`'s `_get_menu_tab_domain`
 * / `_get_menu_tab_filter_domain` / `_get_menu_tab_priority_domain`.
 */
export const messagingMenuHelpers = {
    _get_menu_tab_domain(env, tab_id) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = env["res.users"];
        switch (tab_id) {
            case "bookmark":
                return [["bookmarked_partner_ids", "=", env.user?.partner_id]];
            case "notification":
                return [
                    ["notification_ids.res_partner_id", "=", env.user?.partner_id],
                    ["model", "!=", "discuss.channel"],
                ];
            case "chat":
                return [
                    ["channel_type", "in", ["chat", "group"]],
                    ["default_display_mode", "!=", "video_full_screen"],
                    ["self_member_id.is_pinned", "=", true],
                ];
            case "channel":
                return ResUsers._is_internal(env.uid)
                    ? [
                          ["channel_type", "=", "channel"],
                          "|",
                          ["self_member_id.is_pinned", "=", true],
                          ["message_needaction", "=", true],
                      ]
                    : [
                          ["channel_type", "=", "channel"],
                          ["self_member_id.is_pinned", "=", true],
                      ];
            case "meeting":
                return [
                    ["channel_type", "=", "group"],
                    ["self_member_id.is_pinned", "=", true],
                    "|",
                    ["default_display_mode", "=", "video_full_screen"],
                    ["parent_channel_id.default_display_mode", "=", "video_full_screen"],
                ];
            default:
                return null;
        }
    },
    _get_menu_tab_filter_domain(env, tab_id, filter_id) {
        if (tab_id === "notification" && filter_id === "notification_unread") {
            return [["needaction", "=", true]];
        }
        if (tab_id === "chat" && filter_id === "chat_unread") {
            return [["self_member_id.is_unread", "=", true]];
        }
        return null;
    },
    _get_menu_tab_priority_domain(env, tab_id) {
        return null;
    },
};

/** `tab_id`'s domain, AND'd with `filter_id`'s if given. Throws on an unknown tab/filter
 * (mirrors the real controller's `BadRequest`). */
function _get_menu_tab_full_domain(env, tab_id, filter_id) {
    const domain = messagingMenuHelpers._get_menu_tab_domain(env, tab_id);
    if (!domain) {
        throw new Error(`unknown messaging menu tab "${tab_id}"`);
    }
    if (!filter_id) {
        return domain;
    }
    const filterDomain = messagingMenuHelpers._get_menu_tab_filter_domain(env, tab_id, filter_id);
    if (!filterDomain) {
        throw new Error(`unknown messaging menu filter "${filter_id}" for tab "${tab_id}"`);
    }
    return [...domain, ...filterDomain];
}

/**
 * Resolve `self_member_id.<field>` and `is_member` domain leaves against DiscussChannelMember
 * directly: the mock ORM only resolves dotted domain paths through x2many fields, so these
 * many2one-backed compute/search fields need manual pre-resolution.
 */
function _resolve_self_member_domain(domain) {
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    return domain.map((condition) => {
        if (!Array.isArray(condition) || typeof condition[0] !== "string") {
            return condition;
        }
        if (condition[0] === "is_member") {
            const memberChannelIds = DiscussChannelMember._filter([["is_self", "=", true]]).map(
                (m) => m.channel_id
            );
            return ["id", condition[2] ? "in" : "not in", memberChannelIds];
        }
        if (condition[0].startsWith("self_member_id.")) {
            const memberField = condition[0].slice("self_member_id.".length);
            const matchingChannelIds = DiscussChannelMember._filter([
                ["is_self", "=", true],
                [memberField, condition[1], condition[2]],
            ]).map((m) => m.channel_id);
            return ["id", "in", matchingChannelIds];
        }
        return condition;
    });
}

function _channel_has_needaction(env, channel) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = env["mail.message"];
    if (!env.user) {
        return false;
    }
    return MailMessage._filter([
        ["model", "=", "discuss.channel"],
        ["res_id", "=", channel.id],
    ]).some((message) => MailMessage._needaction(message));
}

registerStoreHandler(
    "/mail/messaging_menu/initialize_counters",
    function store_messaging_menu_initialize_counters(store, params) {
        const { filter_id_by_tab_id_by_record_type = {} } = params;
        const filter_id_by_message_tab_id = filter_id_by_tab_id_by_record_type["mail.message"];
        if (filter_id_by_message_tab_id) {
            /** @type {import("mock_models").MailMessage} */
            const MailMessage = this.env["mail.message"];
            for (const [tab_id, filter_id] of Object.entries(filter_id_by_message_tab_id)) {
                const domain = _get_menu_tab_full_domain(this.env, tab_id, filter_id);
                const messageIds = MailMessage._filter(domain).map((message) => message.id);
                store.add_model_values(
                    "MessagingMenuTab",
                    { init_counter_ids: messageIds },
                    { id_data: { id: tab_id } }
                );
            }
        }
        const filter_id_by_channel_tab_id = filter_id_by_tab_id_by_record_type["discuss.channel"];
        if (!filter_id_by_channel_tab_id) {
            return;
        }
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        DiscussChannelMember._compute_message_unread_counter();
        const unreadChannelIds = new Set();
        for (const member of DiscussChannelMember._filter([
            ["is_self", "=", true],
            ["is_pinned", "=", true],
            ["mute_until_dt", "=", false],
        ])) {
            const [channel] = DiscussChannel.browse(member.channel_id);
            if (!channel || channel.active === false) {
                continue;
            }
            if (member.message_unread_counter || _channel_has_needaction(this.env, channel)) {
                unreadChannelIds.add(channel.id);
            }
        }
        if (ResUsers._is_internal(this.env.uid)) {
            for (const channel of DiscussChannel._filter([["active", "=", true]])) {
                if (_channel_has_needaction(this.env, channel)) {
                    unreadChannelIds.add(channel.id);
                }
            }
        }
        for (const [tab_id, filter_id] of Object.entries(filter_id_by_channel_tab_id)) {
            const domain = _get_menu_tab_full_domain(this.env, tab_id, filter_id);
            const tabChannelIds = DiscussChannel.search([
                ["id", "in", [...unreadChannelIds]],
                ..._resolve_self_member_domain.call(this, domain),
            ]);
            store.add_model_values(
                "MessagingMenuTab",
                { init_counter_ids: tabChannelIds },
                { id_data: { id: tab_id } }
            );
        }
    },
    { audience: "everyone" }
);

registerStoreHandler(
    "/mail/messaging_menu/mail.message/load_more",
    function store_messaging_menu_mail_message_load_more(store, params) {
        const { tab_id, filter_id, exclude_ids, limit, search_term } = params;
        const domain = _get_menu_tab_full_domain(this.env, tab_id, filter_id);
        if (exclude_ids?.length) {
            domain.push(["id", "not in", exclude_ids]);
        }
        const messages = _resolve_messages.call(this, store, { domain, limit, search_term });
        if (messages.length) {
            store.add_inbox_fields = true;
        }
        store.resolve_data_request((res) => res.attr("is_fully_loaded", messages.length < limit));
    }
);

registerStoreHandler(
    "/mail/messaging_menu/discuss.channel/load_more",
    function store_messaging_menu_discuss_channel_load_more(store, params) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        const { tab_id, filter_id, exclude_ids, limit, search_term } = params;
        const channelDomain = _get_menu_tab_full_domain(this.env, tab_id, filter_id);
        if (exclude_ids?.length) {
            channelDomain.push(["id", "not in", exclude_ids]);
        }
        if (search_term) {
            channelDomain.push(["name", "ilike", search_term]);
        }
        const resolvedDomain = _resolve_self_member_domain.call(this, channelDomain);
        // Favorites first, plus any tab-specific priority.
        const selfFavoriteChannelIds = DiscussChannelMember._filter([
            ["is_favorite", "=", true],
        ]).map((m) => m.channel_id);
        const priorityDomain = messagingMenuHelpers._get_menu_tab_priority_domain(this.env, tab_id);
        const priority = [
            "|",
            ["id", "in", selfFavoriteChannelIds],
            ...(priorityDomain
                ? _resolve_self_member_domain.call(this, priorityDomain)
                : [["id", "=", false]]),
        ];
        const channelIds = DiscussChannel.search(
            [...resolvedDomain, ...priority],
            makeKwArgs({ limit, order: "last_interest_dt DESC, id DESC" })
        );
        const remaining = limit - channelIds.length;
        if (remaining > 0) {
            const otherIds = DiscussChannel.search(
                [...resolvedDomain, ["id", "not in", channelIds]],
                makeKwArgs({ limit: remaining, order: "last_interest_dt DESC, id DESC" })
            );
            channelIds.push(...otherIds);
        }
        for (const channelId of channelIds) {
            store.request_channel_ids.add(channelId);
        }
        store.add_channels_last_message = true;
        store.add_channels_last_needaction = true;
        store.resolve_data_request({ is_fully_loaded: channelIds.length < limit });
    },
    { audience: "everyone" }
);

registerStoreHandler(
    "/mail/messaging_menu/get_most_popular_channels",
    function store_messaging_menu_get_most_popular_channels(store) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        const countByChannelId = {};
        for (const member of DiscussChannelMember) {
            const [channel] = DiscussChannel.browse(member.channel_id);
            if (channel && channel.channel_type === "channel") {
                countByChannelId[member.channel_id] =
                    (countByChannelId[member.channel_id] || 0) + 1;
            }
        }
        const topChannelIds = Object.entries(countByChannelId)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 3)
            .map(([channelId]) => Number(channelId));
        store.add_global_values((res) =>
            res.many("most_popular_channels", "_store_channel_fields", {
                value: DiscussChannel.browse(topChannelIds),
            })
        );
    },
    { audience: "everyone" }
);
