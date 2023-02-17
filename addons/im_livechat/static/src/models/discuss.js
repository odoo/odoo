/** @odoo-module **/

import { one, Patch } from "@mail/model";

Patch({
    name: "Discuss",
    recordMethods: {
        /**
         * @override
         */
        onInputQuickSearch(value) {
            if (!this.sidebarQuickSearchValue) {
                this.categoryLivechat.open();
            }
            return this._super(value);
        },
    },
    fields: {
        /**
         * Discuss sidebar category for `livechat` channel threads.
         */
        categoryLivechat: one("DiscussSidebarCategory", {
            default: {},
            inverse: "discussAsLivechat",
        }),
    },
});
