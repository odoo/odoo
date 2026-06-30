import { fields, Record } from "@mail/model/export";
import { compareDatetime } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {{
 *   id: string,
 *   text: string,
 *   includesMessage?: (message: import("models").Message) => boolean,
 *   includesChannel?: (channel: import("models").DiscussChannel) => boolean,
 *   isDefault?: boolean,
 * }} MessagingMenuTabFilter
 */

/** @typedef {{id: string, text: string, icon?: string, isDisabled?: () => boolean, onClick: () => void, preventDropdownClose?: boolean}} MessagingMenuTabAction */

/**
 * Defines a messaging menu tab with:
 * - `actions`: buttons shown near the search bar
 * - `filters`: options to narrow the content
 * - content: tab records loaded lazily through `counter`/`loadMore`
 *
 * Content is always filtered server-side using the tab `id` in `MessagingMenuController`.
 *
 * To configure a tab:
 * - Add its `id` to `_get_menu_tab_domain` to define which records it contains.
 * - Add `(tab id, filter id)` to `_get_menu_tab_filter_domain` to define filter results.
 * - Add its `id` to `_get_menu_tab_priority_domain` to load specific records first.
 *
 * Tabs or filters without matching server-side cases receive no data.
 */
export class MessagingMenuTab extends Record {
    static id = "id";
    static LOAD_MORE_LIMIT = 20;

    /**
     * Actions available next to the search bar.
     *
     * @type {MessagingMenuTabAction}
     */
    actions = [];
    /** @type {?string} */
    activeIcon;
    counter = fields.Attr(0, {
        compute() {
            return this._computeCounter();
        },
    });

    /**
     * Determines if a message should be included in this tab. Centralizes membership
     * logic to avoid scattering it across tab definitions and message model patches. The
     * server-side equivalent is resolved from `id` python side (see
     * `MessagingMenuController._get_menu_tab_domain`).
     *
     * @type {(message: import("models").Message) => boolean}
     */
    includesMessage = () => false;
    /**
     * Drives what is displayed when a tab is empty.
     *
     * @type {{
     *  title?: string,
     *  subtitle?: string,
     *  component?: typeof import("@odoo/owl").Component,
     *  action?: { text: string, onClick: () => void }
     * }}
     */
    emptyState = { title: _t("Nothing here yet.") };
    /** Additional counter not tracked server-side (e.g. failures, push permission request). */
    extraCounter = fields.Attr(0, {
        compute() {
            if (!this.eq(this.store.messagingMenu?.odooBotNotificationsTab)) {
                return 0;
            }
            return (
                (this.store.showPushPermissionRequest ? 1 : 0) +
                this.store.failures.reduce((acc, failure) => acc + failure.notifications.length, 0)
            );
        },
    });
    /**
     * Filters shown as buttons next to the search bar. Selecting a filter narrows the
     * displayed records (client-side via `includesMessage`/`includesChannel`). Its
     * server-side domain equivalent is resolved from `_get_menu_tab_filter_domain`.
     *
     * A filter marked `isDefault` is selected when the tab is opened, and drives the
     * tab's counter badge server-side.
     *
     * @type {MessagingMenuTabFilter}
     */
    filters = [];
    /** Hide the tab from the devtools if really bothered. */
    hidden = fields.Attr(false, { localStorage: true, eager: true });
    hideWhenZeroCounter = false;
    /**
     * Whether this tab contains items that need the user's attention (unread messages,
     * needactions). Impacts both the badge color (red/gray) and whether the count
     * contributes to the global messaging menu counter.
     */
    important = true;
    /** @type {string} */
    icon;
    /** @type {string} */
    id;
    /** Record IDs that were unread at init time, used to compute the `counter` field. */
    init_counter_ids = [];
    label;
    /**
     * Load state tracked per filter. Keyed by filter id, or `"_base"` for the unfiltered
     * view. Values are "new"|"idle"|"loading"|"loaded". See `getLoadStatus`.
     *
     * @type {Object<string, "new"|"idle"|"loading"|"loaded">}
     */
    loadStatusByFilterId = {};
    /** IDs of already loaded records, used to exclude them from `loadMore` requests. */
    loadMoreExcludeIds = fields.Attr([], {
        compute() {
            return this._computeLoadMoreExcludeIds();
        },
    });
    messagingMenuAsTab = fields.One("MessagingMenu", {
        inverse: "allTabs",
        compute() {
            return this.store.messagingMenu;
        },
        eager: true,
    });
    messagingMenuAsVisibleTabs = fields.One("MessagingMenu", {
        inverse: "visibleTabs",
        compute() {
            if (!this.isShown) {
                return;
            }
            return this.store.messagingMenu;
        },
        eager: true,
    });
    messages = fields.Many("mail.message", {
        inverse: "messagingMenuTabsAsMessages",
        sort(m1, m2) {
            return compareDatetime(m2.create_date, m1.create_date) || m2.id - m1.id;
        },
    });
    /** @type {"mail.message"|"discuss.channel"} */
    recordType;
    sequence = 0;

    _computeCounter() {
        // The counter reflects the default filter (when any), so only count loaded
        // messages matching it. `init_counter_ids` is scoped to that domain.
        const defaultFilter = this.defaultFilter;
        const countableMessages = defaultFilter?.includesMessage
            ? this.messages.filter((m) => defaultFilter.includesMessage(m))
            : this.messages;
        const unloadedUnreadCount = this.init_counter_ids.filter(
            (id) => !this.store["mail.message"].get(id)
        ).length;
        return countableMessages.length + unloadedUnreadCount + this.extraCounter;
    }

    _computeLoadMoreExcludeIds() {
        return this.messages.map((m) => m.id);
    }

    get isShown() {
        return !this.hidden && (!this.hideWhenZeroCounter || this.counter > 0);
    }

    /** The filter selected by default when this tab is opened, if any. */
    get defaultFilter() {
        return this.filters.find((f) => f.isDefault);
    }

    /**
     * @param {object} [filter] the active filter, if any
     * @returns {"new"|"idle"|"loading"|"loaded"}
     */
    getLoadStatus(filter) {
        if (this.loadStatusByFilterId["_base"] === "loaded") {
            return "loaded";
        }
        return this.loadStatusByFilterId[filter?.id ?? "_base"] ?? "new";
    }

    /**
     * Fetch the next page of records for this tab, optionally scoped to a filter and/or a
     * search term.
     *
     * @param {object} [options]
     * @param {MessagingMenuTabFilter} [options.filter]
     * @param {string} [options.searchTerm]
     */
    async loadMore({ filter, searchTerm } = {}) {
        if (!["new", "idle"].includes(this.getLoadStatus(filter))) {
            return;
        }
        const key = filter?.id ?? "_base";
        this.loadStatusByFilterId[key] = "loading";
        try {
            const result = await this.store.fetchStoreData(
                `/mail/messaging_menu/${this.recordType}/load_more`,
                {
                    tab_id: this.id,
                    filter_id: filter?.id,
                    exclude_ids: this.loadMoreExcludeIds,
                    limit: MessagingMenuTab.LOAD_MORE_LIMIT,
                    search_term: searchTerm,
                },
                { requestData: true }
            );
            if (!searchTerm) {
                this.loadStatusByFilterId[key] = result.is_fully_loaded ? "loaded" : "idle";
            }
        } finally {
            if (this.loadStatusByFilterId[key] === "loading") {
                this.loadStatusByFilterId[key] = "idle";
            }
        }
    }
}

MessagingMenuTab.register();
