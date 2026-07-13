import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { useSearch } from "@mail/utils/common/hooks";

import { computed, useEffect } from "@odoo/owl";

import { normalize } from "@web/core/l10n/utils";
import { patch } from "@web/core/utils/patch";

/** @type {MessagingMenu} */
const messagingMenuPatch = {
    setup() {
        super.setup(...arguments);
        this.filteredChannels = computed(() => {
            const channels = this.state().activeTab.channels;
            if (!this.state().selectedFilter?.includesChannel) {
                return channels;
            }
            return channels.filter((c) => this.state().selectedFilter.includesChannel(c));
        });
        this.channels = computed(() => {
            if (this.searchTerm()) {
                return this.channelSearch.results;
            }
            return this.filteredChannels();
        });
        this.channelSearch = useSearch({
            fetch: (searchTerm) =>
                this.state().activeTab.loadMore({
                    filter: this.state().selectedFilter,
                    searchTerm,
                }),
            filter: (term) =>
                this.filteredChannels().filter((c) =>
                    normalize(c.displayName).includes(normalize(term))
                ),
            deps: () => [this.filteredChannels()],
        });
        useEffect(() => {
            if (this.state().activeTab.recordType === "discuss.channel") {
                this.channelSearch.searchTerm = this.searchTerm();
            }
        });
        // Bound once so `onClickChannel` is a stable (props.static) handler.
        this.onClickChannel = this.onClickChannel.bind(this);
    },
    get isEmpty() {
        return super.isEmpty && !this.channels().length;
    },
    /** @param {import("models").DiscussChannel} channel */
    onClickChannel(channel) {
        channel.open({ focus: true, fromMessagingMenu: true, bypassCompact: true });
        this.close?.();
    },
};
patch(MessagingMenu.prototype, messagingMenuPatch);
