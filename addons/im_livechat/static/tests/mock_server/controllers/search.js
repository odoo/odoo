import { searchHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { patch } from "@web/core/utils/patch";

patch(searchHelpers, {
    _store_search_channels_extra_fields(store, channels) {
        super._store_search_channels_extra_fields(store, channels);
        const livechats = channels.filter((channel) => channel.channel_type === "livechat");
        store.add(livechats._get_last_messages(), "_store_message_fields");
    },
});
