import { Thread } from "@mail/core/common/thread_model";
import { Record } from "@mail/model/record";
import { rpc } from "@web/core/network/rpc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup(...arguments);
        this.discussAppCategory = Record.one("DiscussAppCategory", {
            compute() {
                return this._computeDiscussAppCategory();
            },
        });
        this.from_message_id = Record.one("mail.message");
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
        /** @type {import("models").Thread|null} */
        this.lastSubChannelLoaded = null;
    },
    get canLeave() {
        return !this.parent_channel_id && super.canLeave;
    },
    get canUnpin() {
        return (this.parent_channel_id && this.importantCounter === 0) || super.canUnpin;
    },
    _computeDiscussAppCategory() {
        if (this.parent_channel_id) {
            return;
        }
        if (["group", "chat"].includes(this.channel_type)) {
            return this.store.discuss.chats;
        }
        if (this.channel_type === "channel") {
            return this.store.discuss.channels;
        }
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
        return ["channel", "group"].includes(this.channel_type) && !this.parent_channel_id;
    },
    get isEmpty() {
        return !this.from_message_id && super.isEmpty;
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
        this.store.Thread.get({ model: "discuss.channel", id: sub_channel }).open({ focus: true });
    },
    /**
     * @param {*} param0
     * @param {string} [param0.searchTerm]
     * @returns {Promise<import("models").Thread[]|undefined>}
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
};
patch(Thread.prototype, threadPatch);
