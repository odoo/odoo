import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread, {
    async getOrFetch(data) {
        let thread = super.get(data);
        if (data.model === "discuss.channel" && data.id) {
            thread = await this.insert({ id: data.id, model: data.model }).fetchChannelInfo();
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
            this._store.channels.fetch();
        }
    },
});
