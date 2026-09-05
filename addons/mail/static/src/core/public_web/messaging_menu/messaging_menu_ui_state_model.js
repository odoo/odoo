import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

export class MessagingMenuUIState extends Record {
    static id = "id";

    activeTab = fields.One("MessagingMenuTab", {
        compute() {
            if (this.activeTab?.isShown) {
                return this.activeTab;
            }
            return this.store.messagingMenu?.sortedVisibleTabs[0];
        },
        eager: true,
        onUpdate() {
            // No tab to show while the menu is still being filled up.
            this.selectedFilter = this.activeTab?.defaultFilter;
            this.pluginFilters = {};
        },
    });
    /**
     * The active chip filter (e.g. "Unread"), if any: rendered as a filter chip, sourced
     * from `tab.filters`.
     *
     * @type {?import("@mail/core/public_web/messaging_menu/messaging_menu_tab_model").MessagingMenuTabFilter}
     */
    selectedFilter;
    /**
     * Extra filters set by addons, keyed by an arbitrary string each addon picks for
     * itself (e.g. `"ai.agent_scope"`). ANDed with the chip filter. Display is up to
     * the addon.
     *
     * @type {Object<string,
     * import("@mail/core/public_web/messaging_menu/messaging_menu_tab_model").MessagingMenuTabFilter>}
     */
    pluginFilters = fields.Attr({}, { asProxy: true });
    /** @type {string} */
    id;
    /**
     * Trigger for the initial tab content load. It recomputes whenever the tab/filter to
     * show changes, or when this state becomes ready to load (see `_isReadyForInitialLoad`).
     */
    _initialLoadTrigger = fields.Attr(null, {
        compute() {
            if (!this._isReadyForInitialLoad() || !this.activeTab) {
                return null;
            }
            const filterKey = this.activeTab._filterKey(
                this.selectedFilter,
                this.activePluginFilters
            );
            return `${this.activeTab.id}__${filterKey}`;
        },
        eager: true,
        onUpdate() {
            this._ensureTabOrFilterInitialLoad();
        },
    });

    /** Currently active plugin filters, as an array. */
    get activePluginFilters() {
        return Object.values(this.pluginFilters).filter(Boolean);
    }

    /**
     * Set or clear (pass `undefined` as the filter) the plugin filter under `key`. Meant
     * for addon code with its own UI that needs to narrow a tab's content, keeping the
     * chip filter.
     *
     * @param {string} key
     * @param {?import("@mail/core/public_web/messaging_menu/messaging_menu_tab_model").MessagingMenuTabFilter} filter
     */
    setPluginFilter(key, filter) {
        if (filter) {
            this.pluginFilters[key] = filter;
        } else {
            delete this.pluginFilters[key];
        }
    }

    /**
     * Handles an explicit tab selection by the user.
     *
     * Unlike setting `activeTab` programmatically, selecting a tab clears the selected
     * thread. This is separate from `activeTab.onUpdate` to avoid clearing threads during
     * programmatic thread-to-tab synchronization.
     *
     * @param {import("models").MessagingMenuTab} tab
     */
    selectTab(tab) {
        this.activeTab = tab;
    }

    /**
     * Whether this state may perform its initial content load. Overridden for the discuss
     * sidebar, which must wait until the thread has been restored from the URL so that
     * `activeTab` has settled on its final value before loading.
     */
    _isReadyForInitialLoad() {
        return true;
    }

    _ensureTabOrFilterInitialLoad() {
        if (this.activeTab.getLoadStatus(this.selectedFilter, this.activePluginFilters) === "new") {
            this.activeTab.loadMore({
                filter: this.selectedFilter,
                pluginFilters: this.activePluginFilters,
            });
        }
    }
}
MessagingMenuUIState.register();
