import { MessagingMenuTab } from "@mail/core/public_web/messaging_menu/messaging_menu_tab_model";
import { compareChannels } from "@mail/discuss/core/public_web/meeting_compare";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").MessagingMenuTab} */
const messagingMenuTabPatch = {
    setup() {
        super.setup(...arguments);
        this.channels = fields.Many("discuss.channel", { inverse: "messagingMenuTabs" });
        this.channelsWithCounter = fields.Many("discuss.channel", {
            inverse: "messagingMenuTabsWithCounter",
        });
        /**
         * Determines if a channel should be included in this tab. Centralizes membership
         * logic to avoid scattering it across tab definitions and channel model patches.
         * The server-side equivalent is resolved from `id` python side (see
         * `DiscussMessagingMenuController._get_menu_tab_domain`).
         *
         * @type {(channel: import("models").DiscussChannel) => boolean}
         */
        this.includesChannel = () => false;
        /**
         * Comparator ordering the channels of this tab, unless the active filter brings its own.
         *
         * @type {(c1: import("models").DiscussChannel, c2: import("models").DiscussChannel) => number}
         */
        this.compareChannels = undefined;
    },

    /**
     * @param {import("models").MessagingMenuTabFilter} [filter]
     * @param {import("models").DiscussChannel[]} [channels]
     */
    getSortedChannels(filter, channels = this.channels) {
        return [...channels].sort(
            filter?.compareChannels ?? this.compareChannels ?? compareChannels
        );
    },

    /** @override */
    canMarkAllAsRead(domain) {
        return this.recordType === "discuss.channel" || super.canMarkAllAsRead(domain);
    },

    /** @override */
    hasUnread(domain) {
        if (this.recordType !== "discuss.channel") {
            return super.hasUnread(domain);
        }
        const isUnread = (channel) => channel.isUnread || channel.needactionCounter > 0;
        if (domain.searchResults) {
            return domain.searchResults.some(isUnread);
        }
        // Counted channels not loaded yet may be listed, whatever the filters.
        if (this._getUnloadedCounterIds().length) {
            return true;
        }
        return this.channels.some(
            (channel) =>
                isUnread(channel) &&
                domain.filters.every((f) => !f.includesChannel || f.includesChannel(channel))
        );
    },

    /** @override */
    async markAllAsRead(domain) {
        if (this.recordType !== "discuss.channel") {
            return super.markAllAsRead(domain);
        }
        const { filters, searchResults } = domain ?? this.getCounterDomain();
        const filterIds = filters.map((f) => f.id);
        const params = {
            tab_id: this.id,
            filter_ids: filterIds,
            channel_ids: searchResults?.map((channel) => channel.id),
        };
        const promises = [
            this.store.fetchStoreData(
                "/mail/messaging_menu/discuss.channel/mark_all_as_read",
                params,
                { requestData: true }
            ),
        ];
        if (this.store.self_user?.share === false) {
            promises.push(
                this.store.fetchStoreData(
                    "/mail/messaging_menu/discuss.channel/set_needaction_done",
                    params,
                    { requestData: true }
                )
            );
        }
        const [unreadResult, needactionResult] = await Promise.all(promises);
        const needactionChannels = needactionResult?.channels ?? [];
        // The bus only updates what is loaded: not the counted channels nor their needactions.
        const readChannelIds = new Set(
            [...unreadResult.channels, ...needactionChannels].map((channel) => channel.id)
        );
        for (const tab of this.store.messagingMenu.allTabs) {
            if (tab.recordType === "discuss.channel") {
                tab.init_counter_ids = tab.init_counter_ids.filter((id) => !readChannelIds.has(id));
            }
        }
        for (const channel of needactionChannels) {
            channel.thread.message_needaction_counter = 0;
        }
        if (searchResults) {
            return;
        }
        // Unread lists within the marked filters are now empty and fully loaded.
        for (const [key, loader] of this.loaderByFilterKey) {
            const keyFilterIds = key.split("__");
            if (
                filterIds.every((filterId) => keyFilterIds.includes(filterId)) &&
                keyFilterIds.some((filterId) => filterId.endsWith("_unread"))
            ) {
                loader.markFullyLoaded();
            }
        }
    },

    /** @override */
    _computeCounter() {
        if (this.recordType !== "discuss.channel") {
            return super._computeCounter();
        }
        return (
            this.channelsWithCounter.length +
            this._getUnloadedCounterIds().length +
            this.extraCounter
        );
    },

    /** Ids of the counted channels that are not loaded yet. */
    _getUnloadedCounterIds() {
        return this.init_counter_ids.filter((id) => {
            const channel = this.store["discuss.channel"].get(id);
            return !channel || channel.fetchChannelInfoState !== "fetched";
        });
    },

    /** @override */
    _computeLoadMoreExcludeIds() {
        if (this.recordType !== "discuss.channel") {
            return super._computeLoadMoreExcludeIds();
        }
        // Exclude channels whose last message is known or loaded by Discuss.
        return this.channels
            .filter(
                (c) =>
                    c.last_message_fetched ||
                    c.thread.eq(this.store.discuss.thread) ||
                    c.thread.isLoaded
            )
            .map((c) => c.id);
    },
};
patch(MessagingMenuTab.prototype, messagingMenuTabPatch);
