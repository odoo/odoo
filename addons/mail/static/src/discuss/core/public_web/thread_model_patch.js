import { Thread } from "@mail/core/common/thread_model";
import { Deferred } from "@web/core/utils/concurrency";
import { Record } from "@mail/model/record";
import { rpc } from "@web/core/network/rpc";

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
    setup() {
        super.setup(...arguments);
        this.owner_id = Record.one("Thread", {
            onDelete() {
                this.delete();
            },
        });
        this.sub_channel_ids = Record.many("Thread", {
            inverse: "owner_id",
            sort: (a, b) => b.id - a.id,
        });
        this.displayInSidebar = Record.attr(false, {
            compute() {
                return (
                    this.displayToSelf ||
                    this.isLocallyPinned ||
                    this.sub_channel_ids.some((t) => t.displayInSidebar)
                );
            },
        });
        this.loadSubChannelsDone = false;
        this.lastSubChannelLoaded = null;
    },
    delete() {
        if (this.model === "discuss.channel") {
            this.store.env.services.bus_service.deleteChannel(this.busChannel);
        }
        super.delete(...arguments);
    },
    /**
     * @param {*} param0
     * @param {string} [param0.searchTerm]
     * @returns {import("models").Thread[]}
     */
    async loadMoreSubChannels({ searchTerm } = {}) {
        if (this.loadSubChannelsDone) {
            return;
        }
        const data = await rpc("/mail/channel/sub_channel/fetch", {
            before: this.lastSubChannelLoaded,
            owner_id: this.id,
            search_term: searchTerm,
        });
        const { Thread: subChannels = [] } = this.store.insert(data, { html: true });
        if (searchTerm) {
            // Ignore holes in the sub-channel list that may arise when
            // searching for a specific term.
            return;
        }
        this.lastSubChannelLoaded = subChannels.at(-1)?.id;
        if (subChannels.length === 0) {
            this.loadSubChannelsDone = true;
        }
        return subChannels;
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
