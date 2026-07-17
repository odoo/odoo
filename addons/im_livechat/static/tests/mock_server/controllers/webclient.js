import { registerStoreHandler } from "@mail/../tests/mock_server/store_handler";

import { serverState } from "@web/../tests/web_test_helpers";

// Mirrors the store handlers of `im_livechat/controllers/webclient.py` (WebClient).

registerStoreHandler(
    "init_livechat",
    function store_init_livechat(store) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        store.add_global_values({ livechat_available: true });
        if (this.env.user && !ResUsers._is_public(this.env.uid)) {
            store.add_global_values((res) =>
                res.one(
                    "self_user",
                    (res) =>
                        res.one("partner_id", (res) => {
                            res.from_method("_store_partner_fields");
                            res.attr("email");
                        }),
                    { value: ResUsers.browse(this.env.user.id) }
                )
            );
        }
        if (this.env.cookie.get("dgid")) {
            store.add_global_values((res) =>
                res.one(
                    "self_guest",
                    (res) => {
                        res.from_method("_store_avatar_fields");
                        res.from_method("_store_im_status_fields");
                    },
                    { value: MailGuest.browse(this.env.cookie.get("dgid")) }
                )
            );
        }
    },
    { audience: "everyone", readonly: false }
);

registerStoreHandler("im_livechat.channel", function store_im_livechat_channel(store) {
    /** @type {import("mock_models").LivechatChannel} */
    const LivechatChannel = this.env["im_livechat.channel"];
    store.add(LivechatChannel.browse(LivechatChannel.search([])), ["are_you_inside", "name"]);
});

registerStoreHandler(
    "/im_livechat/fetch_self_expertise",
    function store_im_livechat_fetch_self_expertise(store) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        store.add(ResUsers.browse(serverState.userId), ["livechat_expertise_ids"]);
    }
);

registerStoreHandler(
    "/im_livechat/looking_for_help",
    function store_im_livechat_looking_for_help(store) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        for (const channelId of DiscussChannel.search([["livechat_status", "=", "need_help"]])) {
            store.request_channel_ids.add(channelId);
        }
    }
);

registerStoreHandler(
    "/im_livechat/session/data",
    function store_im_livechat_session_data(store, { channel_id }) {
        if (!channel_id) {
            return;
        }
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        store.add(
            DiscussChannel.browse(DiscussChannel.search([["id", "=", channel_id]])),
            "_store_livechat_extra_fields"
        );
    }
);
