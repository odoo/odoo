import { fields, Record } from "@mail/model/export";
import { compareDatetime } from "@mail/utils/common/misc";

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {{
 *   id: string,
 *   text: string,
 *   domain: Array,
 *   isDefault?: boolean,
 *   matchesMessage?: (message: import("models").Message) => boolean,
 *   matchesChannel?: (channel: import("models").DiscussChannel) => boolean
 * }[]} MessagingMenuTabFilter
 */

export class MessagingMenuTab extends Record {
    static id = "id";
    static LOAD_MORE_LIMIT = 20;

    /**
     * Actions available next to the search bar.
     *
     * @type {{id: string, text: string, icon?: string, isDisabled?: () => boolean, onClick: () => void}}
     */
    actions = [];
    /** @type {string} */
    activeIcon;
    counter = fields.Attr(0, {
        compute() {
            return this._computeCounter();
        },
    });

    /**
     * ORM domain filtering which records belong to this tab. Used both for lazy-loading
     * tab content and for computing the counter badge. Domain can be omitted when the tab
     * only exists client side (e.g. notification tab).
     *
     * @type {?Array}
     */
    domain;
    /**
     * @type {{ title?: string, subtitle?: string, component?: typeof import("@odoo/owl").Component }}
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
     * Filters shown as buttons next to the search bar. Each filter is an object whose
     * `domain` is ANDed with this tab's base domain. Selecting a filter narrows the
     * displayed records (client-side via `matchesMessage`/`matchesChannel`).
     *
     * A filter marked `isDefault` is selected when the tab is opened, and its combined
     * domain drives the tab's counter badge.
     *
     * @type {MessagingMenuTabFilter}
     */
    filters = [];
    /** Hide the tab from the devtools if really bothered. */
    hidden = fields.Attr(false, { localStorage: true, eager: true });
    /** Hide the tab when it has no unread messages. */
    hideWhenEmpty = false;
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
    loadStatusByFilterId = fields.Attr({});
    /**
     * Optional ORM domain whose matching records are fetched first by `loadMore` (server
     * side). Used e.g. by the livechat tab to display the agent's own channels first.
     *
     * @type {?Array}
     */
    priorityDomain;
    /** IDs of already loaded records, used to exclude them from `loadMore` requests. */
    loadMoreExcludeIds = fields.Attr([], {
        compute() {
            return this._computeLoadMoreExcludeIds();
        },
    });
    /**
     * Determine if a message should be included in this tab. Centralizes membership
     * logic to avoid scattering it across tab definitions and message model patches.
     *
     * @type {(message: import("models").Message) => boolean}
     */
    matchesMessage = () => false;
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
        inverse: "messagingMenuTabsAsMessage",
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
        const countableMessages = defaultFilter?.matchesMessage
            ? this.messages.filter((m) => defaultFilter.matchesMessage(m))
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
        return !this.hidden && (!this.hideWhenEmpty || this.counter > 0);
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
     * @param {object} [options.filter]
     * @param {string} [options.searchTerm]
     */
    async loadMore({ filter, searchTerm } = {}) {
        if (!this.domain || !["new", "idle"].includes(this.getLoadStatus(filter))) {
            return;
        }
        const key = filter?.id ?? "_base";
        this.loadStatusByFilterId[key] = "loading";
        const effectiveDomain = filter ? Domain.and([this.domain, filter.domain]) : this.domain;
        try {
            const result = await this.store.fetchStoreData(
                `/mail/messaging_menu/${this.recordType}/load_more`,
                {
                    domain: Domain.and([
                        effectiveDomain,
                        [["id", "not in", this.loadMoreExcludeIds]],
                    ]).toList({}),
                    limit: MessagingMenuTab.LOAD_MORE_LIMIT,
                    search_term: searchTerm,
                    priority_domain: this.priorityDomain,
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
