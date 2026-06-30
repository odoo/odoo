import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

import { untrack } from "@odoo/owl";

export class MessagingMenuState extends Record {
    static id = "scope";

    activeTab = fields.One("MessagingMenuTab", {
        onUpdate() {
            this.selectedFilter = this.activeTab.defaultFilter;
            this._ensureTabOrFilterInitialLoad();
        },
    });
    /** @type {?import("@mail/core/public_web/messaging_menu/messaging_menu_tab_model").MessagingMenuTabFilter} */
    selectedFilter = fields.Attr(undefined, {
        onUpdate() {
            this._ensureTabOrFilterInitialLoad();
        },
    });
    /** @type {string} */
    scope;

    /**
     * Handles an explicit tab selection by the user.
     *
     * Unlike setting `activeTab` programmatically, selecting a tab clears the selected
     * thread. This is intentionally separate from `activeTab.onUpdate` to avoid clearing
     * threads during programmatic thread-to-tab synchronization.
     *
     * @param {import("models").MessagingMenuTab} tab
     */
    selectTab(tab) {
        this.activeTab = tab;
    }

    _ensureTabOrFilterInitialLoad() {
        untrack(() => {
            if (this.activeTab.getLoadStatus(this.selectedFilter) === "new") {
                this.activeTab.loadMore({ filter: this.selectedFilter });
            }
        });
    }
}
MessagingMenuState.register();
