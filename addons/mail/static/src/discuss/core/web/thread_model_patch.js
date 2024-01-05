/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(Thread, {
    async getOrFetch(data) {
        let thread = super.get(data);
        if (!thread?.channel_type && data.model === "discuss.channel" && data.id) {
            const channelData = await rpc("/discuss/channel/info", { channel_id: data.id });
            if (channelData) {
                thread = this.store.Thread.insert(channelData);
            }
        }
        return thread;
    },
});

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.foldStateCount = 0;
    },
    incrementUnreadCounter() {
        super.incrementUnreadCounter();
        if (this.model === "discuss.channel") {
            // initChannelsUnreadCounter becomes unreliable
            this._store.fetchChannels();
        }
    },
});
