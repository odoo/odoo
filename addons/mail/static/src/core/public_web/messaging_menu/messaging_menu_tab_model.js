import { fields, Record } from "@mail/model/export";
import { ListLoader } from "@mail/utils/common/list_loader";
import { compareDatetime } from "@mail/utils/common/misc";

import { shallowEqual } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {import("models").MessagingMenuTabFilter} MessagingMenuTabFilter
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
 * - `filters`: chip options to narrow the content, rendered next to the search bar
 * - content: tab records loaded lazily through `counter`/`loadMore` (see `ListLoader`)
 *
 * Content can also be narrowed by any number of plugin filters (`pluginFilters`), that
 * can be provided by any addon under its own key (`setPluginFilter`). Display is up to
 * the addon. Every active plugin filter and the chip filter is ANDed together and goes
 * through the same `loadMore` flow.
 *
 * Content is always filtered server-side using the tab `id` in `MessagingMenuController`.
 *
 * To configure a tab:
 * - Add its `id` to `_get_menu_tab_domain` to define which records it contains.
 * - Add `(tab id, filter id)` to `_get_menu_tab_filter_domain` to define filter (chip or
 *   plugin) results.
 * - Add its `id` to `_get_menu_tab_priority_domain` to load specific records first.
 *
 * Tabs or filters without matching server-side cases raise a `BadRequest.
 */
export class MessagingMenuTab extends Record {
    setup() {
        super.setup(...arguments);
        this.onChange(
            () => [this.store.messagingMenu?.initializeCountersFetcher],
            function onChangeInitializeCountersFetcher(initializeCountersFetcher) {
                if (
                    !initializeCountersFetcher ||
                    initializeCountersFetcher.status === "not_fetched"
                ) {
                    return;
                }
                // Dynamic tab missed `initializeCountersFetcher`, catch-up now.
                this.store.fetchStoreData("/mail/messaging_menu/initialize_counters", {
                    filter_id_by_tab_id_by_record_type: {
                        [this.recordType]: { [this.id]: this.defaultFilter?.id ?? null },
                    },
                });
            },
            { immediate: true }
        );
    }

    static id = "id";
    static LOAD_MORE_LIMIT = 20;

    /**
     * Actions available next to the search bar.
     *
     * @type {MessagingMenuTabAction[]}
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
     *  title?: TranslatedString,
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
     * @type {MessagingMenuTabFilter[]}
     */
    filters = [];
    /**
     * Whether this tab is part of the app wide messaging menu: listed in the messaging
     * menu dropdown/discuss sidebar and counted in `globalCounter`. `false` for a tab
     * scoped to a specific context (displayed through its own dedicated UI). Context
     * specific tabs still benefit from lazy-load and counter.
     */
    appWide = true;
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
     * Loaders of the records, per combination of active filters (see `_filterKey`), or
     * `"_base"` for the unfiltered view. See `getLoader`.
     *
     * @type {Map<string, ListLoader>}
     */
    loaderByFilterKey = new Map();
    /** IDs of already loaded records, used to exclude them from `loadMore` requests. */
    loadMoreExcludeIds = this.computed(() => this._computeLoadMoreExcludeIds(), {
        equals: shallowEqual,
    });
    messages = fields.Many("mail.message", { inverse: "messagingMenuTabsAsMessages" });
    sortedMessages = this.computed(
        () =>
            [...this.messages].sort(
                (m1, m2) => compareDatetime(m2.create_date, m1.create_date) || m2.id - m1.id
            ),
        { equals: shallowEqual }
    );
    /** @type {"mail.message"|"discuss.channel"} */
    recordType;
    sequence = 0;

    _computeCounter() {
        // The counter reflects the default filter (when any), so only count loaded
        // messages matching it. `init_counter_ids` is scoped to that domain.
        const defaultFilter = this.defaultFilter;
        const isCountable = (message) =>
            !defaultFilter?.includesMessage || defaultFilter.includesMessage(message);
        const countableMessages = this.messages.filter(isCountable);
        const countedIds = new Set(countableMessages.map((m) => m.id));
        const unloadedUnreadCount = this.init_counter_ids.filter((id) => {
            if (countedIds.has(id)) {
                return false;
            }
            const message = this.store["mail.message"].get(id);
            // Count a loaded message until its own compute links it to this tab.
            return !message || (this.includesMessage(message) && isCountable(message));
        }).length;
        return countableMessages.length + unloadedUnreadCount + this.extraCounter;
    }

    _computeLoadMoreExcludeIds() {
        return this.messages.map((m) => m.id);
    }

    /** Whether `hidden`/`hideWhenZeroCounter` allow this tab to be shown. */
    get canBeShown() {
        return !this.hidden && (!this.hideWhenZeroCounter || this.counter > 0);
    }

    /** The filter selected by default when this tab is opened, if any. */
    get defaultFilter() {
        return this.filters.find((f) => f.isDefault);
    }

    /** Filters in the order they are shown, right after the "All" one. */
    sortedFilters = this.computed(
        () => [...this.filters].sort((f1, f2) => (f1.sequence ?? 0) - (f2.sequence ?? 0)),
        { equals: shallowEqual }
    );

    /**
     * Deterministic key for a given combination of active filters: the chip filter, if
     * any and every currently active plugin filter.
     *
     * @param {MessagingMenuTabFilter} [filter] The active chip filter, if any.
     * @param {MessagingMenuTabFilter[]} [pluginFilters=[]] The active plugin filters.
     * @returns {string}
     */
    _filterKey(filter, pluginFilters = []) {
        const ids = [filter?.id, ...pluginFilters.map((f) => f.id)].filter(Boolean).sort();
        return ids.length ? ids.join("__") : "_base";
    }

    /**
     * @param {MessagingMenuTabFilter} [filter] The active chip filter, if any.
     * @param {MessagingMenuTabFilter[]} [pluginFilters=[]] The active plugin filters.
     * @returns {"new"|"idle"|"loading"|"loaded"}
     */
    getLoadStatus(filter, pluginFilters = []) {
        if (this.getLoader("_base").getStatus("older") === "loaded") {
            return "loaded";
        }
        return this.getLoader(this._filterKey(filter, pluginFilters)).getStatus("older");
    }

    /**
     * @param {string} filterKey see `_filterKey`
     * @returns {ListLoader}
     */
    getLoader(filterKey) {
        if (!this.loaderByFilterKey.has(filterKey)) {
            this.loaderByFilterKey.set(filterKey, this._makeLoader(filterKey));
        }
        return this.loaderByFilterKey.get(filterKey);
    }

    /**
     * Fetch the next page of records for this tab, optionally scoped to a chip filter, any
     * number of plugin filters, and/or a search term. All active filters are ANDed together
     * server-side (see `MessagingMenuController._get_menu_tab_full_domain`).
     *
     * @param {object} [options]
     * @param {MessagingMenuTabFilter} [options.filter]
     * @param {MessagingMenuTabFilter[]} [options.pluginFilters]
     * @param {string} [options.searchTerm]
     */
    async loadMore({ filter, pluginFilters = [], searchTerm } = {}) {
        const filterKey = this._filterKey(filter, pluginFilters);
        if (searchTerm) {
            // Search results are fetched apart from the loaded records: they don't affect them.
            const params = { search_term: searchTerm };
            await this._makeLoader(filterKey).load("older", { params });
            return;
        }
        if (this.getLoadStatus(filter, pluginFilters) !== "loaded") {
            await this.getLoader(filterKey).load("older");
        }
    }

    /** @param {string} filterKey see `_filterKey` */
    _makeLoader(filterKey) {
        return new ListLoader({
            fetch: async (params) => {
                const result = await this.store.fetchStoreData(
                    `/mail/messaging_menu/${this.recordType}/load_more`,
                    {
                        tab_id: this.id,
                        filter_ids: filterKey === "_base" ? [] : filterKey.split("__"),
                        ...params,
                    },
                    { requestData: true }
                );
                return this.recordType === "mail.message" ? result.messages : result.channels;
            },
            getKnownIds: () => this.loadMoreExcludeIds,
            limit: MessagingMenuTab.LOAD_MORE_LIMIT,
        });
    }
}

MessagingMenuTab.register();
