import { _resolve_messages } from "@mail/../tests/mock_server/mail_mock_server";
import {
    registerStoreHandler,
    storeHandlerRegistry,
} from "@mail/../tests/mock_server/store_handler";

import { makeKwArgs } from "@web/../tests/web_test_helpers";

// Mirrors the store handlers of `mail/controllers/discuss/channel.py`
// (DiscussChannelWebclientController).

registerStoreHandler(
    "has_hidden_channels",
    function store_has_hidden_channels(store) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        // is_self is computed per current persona; the mock only computes it at create/write time
        // (matching py's depends_context('uid','guest') field, which is always evaluated for the
        // requesting user). Refresh it here so is_self filters resolve for the authenticated user.
        DiscussChannelMember.browse(DiscussChannelMember.search([]))._compute_is_self();
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        const hiddenMemberChannelIds = DiscussChannelMember.browse(
            DiscussChannelMember.search([
                ["is_self", "=", true],
                ["is_pinned", "=", false],
            ])
        ).map((member) => member.channel_id);
        store.add_global_values({
            // discuss.channel search drops archived channels (active=true), like py `channel_id.active`.
            has_hidden_channels:
                DiscussChannel.search([["id", "in", hiddenMemberChannelIds]]).length > 0,
        });
    },
    { audience: "everyone" }
);

registerStoreHandler(
    "channels_as_member",
    function store_channels_as_member(store) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        for (const channel of DiscussChannel._get_channels_as_member()) {
            store.request_channel_ids.add(channel.id);
        }
        store.add_channels_last_message = true;
        storeHandlerRegistry.handlers.store_has_hidden_channels.call(this, store);
    },
    { audience: "everyone" }
);

registerStoreHandler(
    "discuss.channel",
    function store_add_discuss_channel_to_context(store, params) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        const { ids, with_last_message } = params;
        for (const channelId of DiscussChannel.search([["id", "=", ids]])) {
            store.request_channel_ids.add(channelId);
        }
        if (with_last_message) {
            store.add_channels_last_message = true;
        }
    },
    { audience: "everyone" }
);

registerStoreHandler(
    "/discuss/channel/members",
    function store_get_discuss_channel_members(store, params) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        const { channel_id, known_member_ids = [], search_term } = params;
        let memberIds = DiscussChannelMember.search(
            [
                ["id", "not in", known_member_ids],
                ["channel_id", "=", channel_id],
            ],
            makeKwArgs({ limit: 100 })
        );
        if (search_term) {
            const lowerTerm = search_term.toLowerCase();
            memberIds = DiscussChannelMember.browse(memberIds)
                .filter((member) => {
                    if (member.partner_id) {
                        const [partner] = ResPartner.browse(member.partner_id);
                        return partner?.name?.toLowerCase().includes(lowerTerm);
                    }
                    if (member.guest_id) {
                        const [guest] = MailGuest.browse(member.guest_id);
                        return guest?.name?.toLowerCase().includes(lowerTerm);
                    }
                    return false;
                })
                .map((member) => member.id);
        }
        const memberCount = DiscussChannelMember.search_count([["channel_id", "=", channel_id]]);
        store.add(DiscussChannel.browse(channel_id), { member_count: memberCount });
        store.add(DiscussChannelMember.browse(memberIds), "_store_member_fields");
    },
    { audience: "everyone" }
);

registerStoreHandler(
    "/discuss/channel/favorite",
    function store_set_discuss_channel_favorite(store, params) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        const memberIds = DiscussChannelMember.search([
            ["channel_id", "=", params.channel_id],
            ["is_self", "=", true],
        ]);
        if (memberIds.length) {
            DiscussChannelMember.write(memberIds, { is_favorite: params.is_favorite });
        }
    },
    { audience: "everyone", readonly: false }
);

registerStoreHandler(
    "/discuss/channel/messages",
    function store_get_discuss_channel_messages(store, params) {
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        const channel = this.env["discuss.channel"].browse(params.channel_id);
        const messages = _resolve_messages.call(this, store, {
            ...params.fetch_params,
            domain: [],
            thread: channel,
        });
        MailMessage.set_message_done(messages.map((message) => message.id));
    },
    { audience: "everyone", readonly: false }
);

registerStoreHandler(
    "/discuss/channel/pin",
    function store_set_discuss_channel_pin(store, params) {
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        const memberIds = DiscussChannelMember.search([
            ["channel_id", "=", params.channel_id],
            ["is_self", "=", true],
        ]);
        DiscussChannelMember._channel_pin(memberIds, params.pinned);
        storeHandlerRegistry.handlers.store_has_hidden_channels.call(this, store);
    },
    { audience: "everyone", readonly: false }
);

registerStoreHandler(
    "/discuss/get_or_create_chat",
    function store_get_or_create_chat(store, params) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        const channelId = DiscussChannel._get_or_create_chat(params.partners_to);
        if (channelId) {
            store.resolve_data_request((res) =>
                res.one("channel", "_store_channel_fields", { value: channelId })
            );
            storeHandlerRegistry.handlers.store_has_hidden_channels.call(this, store);
        }
    },
    { audience: "everyone", readonly: false }
);

registerStoreHandler(
    "/discuss/create_channel",
    function store_create_channel(store, params) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        const channelId = DiscussChannel._create_channel(
            params.name,
            params.group_id,
            params.is_readonly
        );
        store.resolve_data_request((res) =>
            res.one("channel", "_store_channel_fields", { value: channelId })
        );
    },
    { audience: "everyone", readonly: false }
);

registerStoreHandler(
    "/discuss/channel/add_members",
    function store_discuss_channel_add_members(store, params) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        DiscussChannel._add_members(
            [params.channel_id],
            makeKwArgs({
                partner_ids: params.partner_ids,
                user_ids: params.user_ids,
                invite_to_rtc_call: params.invite_to_rtc_call,
                post_joined_message: params.post_joined_message,
            })
        );
    },
    { audience: "logged_in", readonly: false }
);

registerStoreHandler(
    "/discuss/create_group",
    function store_create_group(store, params) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        const channelId = DiscussChannel._create_group(
            params.users_to,
            params.default_display_mode,
            params.name
        );
        store.resolve_data_request((res) =>
            res.one("channel", "_store_channel_fields", { value: channelId })
        );
    },
    { audience: "everyone", readonly: false }
);
