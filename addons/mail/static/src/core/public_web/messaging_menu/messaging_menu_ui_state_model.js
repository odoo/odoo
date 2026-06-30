import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

export class MessagingMenuUIState extends Record {
    static id = "id";

    activeTab = fields.One("MessagingMenuTab", {
        compute() {
            if (this.activeTab?.isShown) {
                return this.activeTab;
            }
            return this.store.messagingMenu?.visibleTabs[0];
        },
        eager: true,
        onUpdate() {
            this.selectedFilter = this.activeTab.defaultFilter;
        },
    });
    /** @type {?import("@mail/core/public_web/messaging_menu/messaging_menu_tab_model").MessagingMenuTabFilter} */
    selectedFilter;
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
            return `${this.activeTab.id}::${this.selectedFilter?.id ?? ""}`;
        },
        eager: true,
        onUpdate() {
            this._ensureTabOrFilterInitialLoad();
        },
    });

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
        if (this.activeTab.getLoadStatus(this.selectedFilter) === "new") {
            this.activeTab.loadMore({ filter: this.selectedFilter });
        }
    }
}
MessagingMenuUIState.register();
