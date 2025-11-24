import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/misc";
import { compareDatetime } from "@mail/utils/common/misc";
import { rpc } from "@web/core/network/rpc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup(...arguments);
        this.appAsUnreadChannels = fields.One("DiscussApp", {
            compute() {
                return this.channel_type === "channel" && this.isUnread ? this.store.discuss : null;
            },
        });
        this.categoryAsThreadWithCounter = fields.One("DiscussAppCategory", {
            compute() {
                return this.displayInSidebar && this.importantCounter > 0
                    ? this.discussAppCategory
                    : null;
            },
        });
        this.discussAppCategory = fields.One("DiscussAppCategory", {
            compute() {
                return this._computeDiscussAppCategory();
            },
        });
        this.from_message_id = fields.One("mail.message");
        this.parent_channel_id = fields.One("Thread", {
            onDelete() {
                this.delete();
            },
        });
        this.sub_channel_ids = fields.Many("Thread", {
            inverse: "parent_channel_id",
            sort: (a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id,
        });
        this.displayInSidebar = fields.Attr(false, {
            compute() {
                return this._computeDisplayInSidebar();
            },
        });
        this.loadSubChannelsDone = false;
        /** @type {import("models").Thread|null} */
        this.lastSubChannelLoaded = null;
    },
    get canLeave() {
        return !this.parent_channel_id && super.canLeave;
    },
    _computeDisplayInSidebar() {
        return (
            this.displayToSelf ||
            this.isLocallyPinned ||
            this.sub_channel_ids.some((t) => t.displayInSidebar)
        );
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
    get hasSubChannelFeature() {
        return ["channel", "group"].includes(this.channel_type);
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
        const { store_data, sub_channel } = await rpc("/discuss/channel/sub_channel/create", {
            parent_channel_id: this.parent_channel_id?.id || this.id,
            from_message_id: initialMessage?.id,
            name,
        });
        this.store.insert(store_data);
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
        const { store_data, sub_channel_ids } = await rpc("/discuss/channel/sub_channel/fetch", {
            before: this.lastSubChannelLoaded?.id,
            limit,
            parent_channel_id: this.id,
            search_term: searchTerm,
        });
        this.store.insert(store_data);
        const threads = sub_channel_ids.map((subChannelId) =>
            this.store.Thread.get({ model: "discuss.channel", id: subChannelId })
        );

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
        if (this.self_member_id?.is_pinned) {
            this.isLocallyPinned = false;
        }
        if (!this.self_member_id?.is_pinned && !this.isLocallyPinned) {
            this.sub_channel_ids.forEach((c) => (c.isLocallyPinned = false));
        }
    },
    /** @override */
    openChannel() {
        if (this.store.discuss.isActive && !this.store.env.services.ui.isSmall) {
            this.setAsDiscussThread();
            return true;
        }
        return super.openChannel();
    },
    setAsDiscussThread() {
        super.setAsDiscussThread(...arguments);
        if (!this.displayToSelf && this.model === "discuss.channel") {
            this.isLocallyPinned = true;
        }
    },
};
patch(Thread.prototype, threadPatch);
