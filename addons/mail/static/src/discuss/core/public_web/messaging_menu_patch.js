import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { useSearch } from "@mail/utils/common/hooks";

import { computed, signal, useEffect } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { normalize } from "@web/core/l10n/utils";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { computedShallowEqual } from "@mail/utils/common/signal";

/** @type {MessagingMenu} */
const messagingMenuPatch = {
    setup() {
        super.setup(...arguments);
        this.unreadConversationCount = signal(0);
        this.filteredChannels = computedShallowEqual(() => {
            const filters = [...this.state().activePluginFilters];
            if (this.state().selectedFilter) {
                filters.push(this.state().selectedFilter);
            }
            const channels = this.state().activeTab.channels.filter((c) =>
                filters.every((f) => !f.includesChannel || f.includesChannel(c))
            );
            return this.state().activeTab.getSortedChannels(this.state().selectedFilter, channels);
        });
        this.channels = computed(() => {
            if (this.state().searchTerm) {
                return this.channelSearch.results;
            }
            return this.filteredChannels();
        });
        this.channelSearch = useSearch({
            fetch: (searchTerm) =>
                this.state().activeTab.loadMore({
                    filter: this.state().selectedFilter,
                    pluginFilters: this.state().activePluginFilters,
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
                this.channelSearch.searchTerm = this.state().searchTerm;
            }
        });
        // Bound once so `onClickChannel` is a stable (useProps.static) handler.
        this.onClickChannel = this.onClickChannel.bind(this);
    },
    get isEmpty() {
        return super.isEmpty && !this.channels().length;
    },
    getUnreadConversationParams() {
        return {
            tab_id: this.activeTab().id,
            filter_ids: [
                this.state().selectedFilter?.id,
                ...this.state().activePluginFilters.map((filter) => filter.id),
            ].filter(Boolean),
            search_term: this.state().searchTerm,
        };
    },
    get markAllReadItems() {
        return [
            {
                label: _t("Mark All as Read"),
                class: this.unreadConversationCount() ? "" : "disabled text-muted",
                onSelected: () => this.onClickMarkAllRead(),
            },
        ];
    },
    async refreshUnreadConversationCount() {
        const params = this.getUnreadConversationParams();
        const requestId = this.unreadConversationCountRequestId =
            (this.unreadConversationCountRequestId ?? 0) + 1;
        this.unreadConversationCount.set(0);
        const count = await rpc("/discuss/messaging_menu/unread_count", params, { silent: true });
        if (requestId === this.unreadConversationCountRequestId) {
            this.unreadConversationCount.set(count);
        }
    },
    onClickMarkAllRead() {
        if (!this.unreadConversationCount()) {
            return;
        }
        const params = this.getUnreadConversationParams();
        this.dialog.add(ConfirmationDialog, {
            title: _t("Mark All Read"),
            body: _t("Are you sure you want to mark all unread conversations as read?"),
            confirmLabel: _t("Confirm"),
            cancelLabel: _t("Discard"),
            confirm: async () => {
                const ids = await rpc("/discuss/messaging_menu/mark_all_as_read", params);
                const readIds = new Set(ids);
                for (const tab of this.store.messagingMenu.allTabs) {
                    if (tab.recordType === "discuss.channel") {
                        tab.init_counter_ids = tab.init_counter_ids.filter((id) => !readIds.has(id));
                    }
                }
                this.unreadConversationCount.set(0);
            },
        });
    },
    /** @param {import("models").DiscussChannel} channel */
    async onClickChannel(channel) {
        this.channelToOpen = channel;
        const prefetchingOrTimeout = channel.thread?.prefetchingOrTimeout;
        if (prefetchingOrTimeout) {
            // Wait for the prefetch, so the thread shows already loaded instead of
            // rendering once empty and again once it resolves.
            const activeTab = this.state().activeTab;
            await prefetchingOrTimeout;
            if (this.channelToOpen !== channel || this.state().activeTab !== activeTab) {
                return;
            }
        }
        channel.open({ focus: true, fromMessagingMenu: true, bypassCompact: true });
        this.close?.();
    },
};
patch(MessagingMenu.prototype, messagingMenuPatch);
