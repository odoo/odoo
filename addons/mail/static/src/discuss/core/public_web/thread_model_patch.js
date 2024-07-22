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
        if (thread.fetchChannelInfoState === "fetching") {
            return thread.fetchChannelInfoDeferred;
        }
        thread.fetchChannelInfoState = "fetching";
        const def = new Deferred();
        thread.fetchChannelInfoDeferred = def;
        thread.fetchChannelInfo().then(
            (result) => {
                if (thread.exists()) {
                    thread.fetchChannelInfoState = "fetched";
                    thread.fetchChannelInfoDeferred = undefined;
                }
                def.resolve(result);
            },
            (error) => {
                if (thread.exists()) {
                    thread.fetchChannelInfoState = "not_fetched";
                    thread.fetchChannelInfoDeferred = undefined;
                }
                def.reject(error);
            }
        );
        return def;
    },
});

patch(Thread.prototype, {
    delete() {
        if (this.model === "discuss.channel") {
            this.store.env.services.bus_service.deleteChannel(this.busChannel);
        }
        super.delete(...arguments);
    },

    onPinStateUpdated() {
        super.onPinStateUpdated();
        if (this.is_pinned) {
            this.isLocallyPinned = false;
        }
        if (this.isLocallyPinned) {
            this.store.env.services["bus_service"].addChannel(this.busChannel);
        } else {
            this.store.env.services["bus_service"].deleteChannel(this.busChannel);
        }
    },
    setAsDiscussThread() {
        super.setAsDiscussThread(...arguments);
        if (!this.displayToSelf && this.model === "discuss.channel") {
            this.isLocallyPinned = true;
        }
    },
});
