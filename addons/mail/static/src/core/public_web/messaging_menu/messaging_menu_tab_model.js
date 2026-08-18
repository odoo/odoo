import { Record, fields } from "@mail/model/export";
import { compareDatetime } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {{
 *   id: string,
 *   text: string,
 *   includesMessage?: (message: import("models").Message) => boolean,
 *   includesChannel?: (channel: import("models").DiscussChannel) => boolean,
 *   isDefault?: boolean,
 *   sequence?: number,
 *   compareChannels?: (c1: import("models").DiscussChannel, c2: import("models").DiscussChannel) => number,
 * }} MessagingMenuTabFilter
 *
 * The channels of a tab are ordered by the comparator of the active filter, falling back to the
 * one of the tab, then to the default order of the messaging menu.
 */

/**
 * A button shown next to the search bar. An action carrying `subActions` is rendered as a
 * dropdown offering them instead: clicking it only opens the menu, so such an action has no
 * `onClick` of its own.
 *
 * @typedef {{
 *   id: string,
 *   text: string,
 *   icon?: string,
 *   iconClass?: string,
 *   isDisabled?: () => boolean,
 *   onClick?: () => void,
 *   preventDropdownClose?: boolean,
 *   subActions?: MessagingMenuTabAction[],
 * }} MessagingMenuTabAction
 */

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
    counter = this.computed(() => this._computeCounter());

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
    extraCounter = this.computed(() => {
        if (!this.eq(this.store.messagingMenu?.odooBotNotificationsTab)) {
            return 0;
        }
        return (
            (this.store.showPushPermissionRequest ? 1 : 0) +
            this.store.failures.reduce((acc, failure) => acc + failure.notifications.length, 0)
        );
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
    hidden = this.localStorage(false);
    hideWhenZeroCounter = false;
    /**
     * Whether this tab contains items that need the user's attention (unread messages,
     * needactions). Impacts both the badge color (red/gray) and whether the count
     * contributes to the global messaging menu counter.
     */
    important = true;
    /** @type {string} */
    icon;
    /** @type {string|undefined} extra classes for the icon */
    iconClass;
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
    loadStatusByFilterId = fields.Attr({}, { asProxy: true });
    /** IDs of already loaded records, used to exclude them from `loadMore` requests. */
    loadMoreExcludeIds = this.computed(() => this._computeLoadMoreExcludeIds());
    messages = fields.Many("mail.message", { inverse: "messagingMenuTabsAsMessages" });
    get sortedMessages() {
        return [...this.messages].sort(
            (m1, m2) => compareDatetime(m2.create_date, m1.create_date) || m2.id - m1.id
        );
    }
    /** @type {"mail.message"|"discuss.channel"} */
    recordType;
    sequence = 0;

    get isShown() {
        return !this.hidden && (!this.hideWhenZeroCounter || this.counter > 0);
    }

    /** The filter selected by default when this tab is opened, if any. */
    get defaultFilter() {
        return this.filters.find((f) => f.isDefault);
    }

    /** Filters in the order they are shown, right after the "All" one. */
    get sortedFilters() {
        return [...this.filters].sort((f1, f2) => (f1.sequence ?? 0) - (f2.sequence ?? 0));
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
}

MessagingMenuTab.register();
