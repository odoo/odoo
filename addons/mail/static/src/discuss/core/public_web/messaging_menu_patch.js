import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { useSearch } from "@mail/utils/common/hooks";

import { computed, useEffect } from "@odoo/owl";

import { normalize } from "@web/core/l10n/utils";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.filteredChannels = computed(() => {
            const channels = this.state().activeTab.channels;
            if (!this.state().selectedFilter?.matchesChannel) {
                return channels;
            }
            return channels.filter((c) => this.state().selectedFilter.matchesChannel(c));
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
    },
    get isEmpty() {
        return super.isEmpty && !this.channels().length;
    },
    onClickChannel(channel) {
        channel.open({ focus: true, fromMessagingMenu: true, bypassCompact: true });
        this.close?.();
    },
});
