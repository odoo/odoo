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
        this.from_message_id = Record.one("Message");
        this.parent_channel_id = Record.one("Thread", {
            onDelete() {
                this.delete();
            },
        });
        this.sub_channel_ids = Record.many("Thread", {
            inverse: "parent_channel_id",
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
    get canLeave() {
        return !this.parent_channel_id && super.canLeave;
    },
    get canUnpin() {
        return (this.parent_channel_id && this.importantCounter === 0) || super.canUnpin;
    },
    get allowCalls() {
        return super.allowCalls && !this.parent_channel_id;
    },
    delete() {
        if (this.model === "discuss.channel") {
            this.store.env.services.bus_service.deleteChannel(this.busChannel);
        }
        super.delete(...arguments);
    },
    get hasSubChannelFeature() {
        return this.channel_type === "channel" && !this.parent_channel_id;
    },
    get isEmpty() {
        return !this.from_message_id && super.isEmpty;
    },
    get notifyOnLeave() {
        return super.notifyOnLeave && !this.parent_channel_id;
    },
    /**
     * @param {Object} [param0={}]
     * @param {import("models").Message} [param0.initialMessage]
     * @param {string} [param0.name]
     */
    async createSubChannel({ initialMessage, name } = {}) {
        const { data, sub_channel } = await rpc("/discuss/channel/sub_channel/create", {
            parent_channel_id: this.id,
            from_message_id: initialMessage?.id,
            name,
        });
        this.store.insert(data, { html: true });
        this.store.Thread.get(sub_channel).open();
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
        const limit = 30;
        const data = await rpc("/discuss/channel/sub_channel/fetch", {
            before: this.lastSubChannelLoaded?.id,
            limit,
            parent_channel_id: this.id,
            search_term: searchTerm,
        });
        const { Thread: threads = [] } = this.store.insert(data, { html: true });
        if (searchTerm) {
            // Ignore holes in the sub-channel list that may arise when
            // searching for a specific term.
            return;
        }
        const subChannels = threads.filter((thread) => this.eq(thread.parent_channel_id));
        this.lastSubChannelLoaded = subChannels.reduce(
            (min, channel) => (!min || channel.id < min.id ? channel : min),
            this.lastSubChannelLoaded
        );
        if (subChannels.length < limit) {
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
        if (!this.is_pinned && !this.isLocallyPinned) {
            this.sub_channel_ids.forEach((c) => (c.isLocallyPinned = false));
        }
    },
    setAsDiscussThread() {
        super.setAsDiscussThread(...arguments);
        if (!this.displayToSelf && this.model === "discuss.channel") {
            this.isLocallyPinned = true;
        }
    },
});
