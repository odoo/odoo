import { registerStoreHandler } from "@mail/../tests/mock_server/store_handler";

// Mirrors the store handlers of `mail/controllers/discuss/public_page.py` (PublicPageController).

registerStoreHandler(
    "/discuss/channel/join_from_invitation",
    function store_discuss_channel_join_from_invitation(store, params) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        const { channel_id, guest_name } = params;
        DiscussChannel._find_or_create_persona_for_channel(channel_id, guest_name);
        store.request_channel_ids.add(channel_id);
    },
    { audience: "everyone", readonly: false }
);
