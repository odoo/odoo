import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/misc";

import { router } from "@web/core/browser/router";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup(...arguments);
<<<<<<< 5d18a9e458b9414b32bc9801c6b83bedafc8ad27
||||||| 2504d010c2fdb107961a0d57d564d021b36a08c1
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
=======
        this.appAsUnreadChannels = fields.One("DiscussApp", {
            compute() {
                return this.channel_type === "channel" && this.isUnread ? this.store.discuss : null;
            },
        });
        this.categoryAsThreadWithCounter = fields.One("DiscussAppCategory", {
            compute() {
                // Sub channels have no category, they are displayed in the one of their parent.
                return this.displayInSidebar && this.importantCounter > 0
                    ? this.discussAppCategory ?? this.parent_channel_id?.discussAppCategory
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
>>>>>>> 52fd39ff365c8c53c5795ac3b9e3b59b4b9ecefe
        this.loadSubChannelsDone = false;
        this.lastSubChannelLoaded = fields.One("discuss.channel");
    },
    get hasSubChannelFeature() {
        return ["channel", "group"].includes(this.channel?.channel_type);
    },
    get isEmpty() {
        return !this.channel?.from_message_id && super.isEmpty;
    },
    /**
     * @param {Object} [param0={}]
     * @param {import("models").Message} [param0.initialMessage]
     * @param {string} [param0.name]
     */
    async createSubChannel({ initialMessage, name } = {}) {
        const { store_data, sub_channel } = await rpc("/discuss/channel/sub_channel/create", {
            parent_channel_id: this.channel?.parent_channel_id?.id || this.id,
            from_message_id: initialMessage?.id,
            name,
        });
        this.store.insert(store_data);
        this.store["discuss.channel"].get(sub_channel).open({ focus: true });
    },
    async leaveChannelProcess() {
        this.channel.isLocallyPinned = false;
        if (this.discussAppAsThread) {
            router.replaceState({ active_id: undefined });
        }
        await super.leaveChannelProcess(...arguments);
    },
    /**
     * @param {*} param0
     * @param {string} [param0.searchTerm]
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
        const channels = sub_channel_ids.map((id) => this.store["discuss.channel"].get(id));
        if (searchTerm) {
            // Ignore holes in the sub-channel list that may arise when
            // searching for a specific term.
            return;
        }
        const subChannels = channels.filter((channel) =>
            this.channel.eq(channel.parent_channel_id)
        );
        this.lastSubChannelLoaded = subChannels.reduce(
            (min, channel) => (!min || channel.id < min.id ? channel : min),
            this.lastSubChannelLoaded
        );
        if (subChannels.length < limit) {
            this.loadSubChannelsDone = true;
        }
    },
    setAsDiscussThread() {
        super.setAsDiscussThread(...arguments);
        if (this.channel && !this.channel?.self_member_id?.is_pinned) {
            this.channel.isLocallyPinned = true;
        }
    },
};
patch(Thread.prototype, threadPatch);
