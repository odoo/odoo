import { Thread } from "@mail/core/common/thread_model";
import { Deferred } from "@web/core/utils/concurrency";

import { patch } from "@web/core/utils/patch";

patch(Thread, {
    async getOrFetch(data) {
        let thread = super.get(data);
        if (data.model !== "discuss.channel" || !data.id) {
            return thread;
        }
        thread = this.insert({ id: data.id, model: data.model });
        if (thread.fetchChannelInfoState === "fetched") {
            return Promise.resolve(thread);
        }
        if (thread.fetchChannelInfoStateState === "fetching") {
            return thread.fetchChannelInfoDeferred;
        }
        thread.fetchChannelInfoState = "fetching";
        thread.fetchChannelInfoDeferred = new Deferred();
        thread.fetchChannelInfo().then(
            (result) => {
                thread.fetchChannelInfoState = "fetched";
                thread.fetchChannelInfoDeferred.resolve(result);
                thread.fetchChannelInfoDeferred = undefined;
            },
            (error) => {
                thread.fetchChannelInfoState = "not_fetched";
                thread.fetchChannelInfoDeferred.reject(error);
                thread.fetchChannelInfoDeferred = undefined;
            }
        );
        return thread.fetchChannelInfoDeferred;
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
