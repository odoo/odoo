/* @odoo-module */

import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    /**
     * @override
     */
    tabToThreadType(tab) {
        const threadTypes = super.tabToThreadType(tab);
        if (tab === "chat" && !this.env.services.ui.isSmall) {
            threadTypes.push("livechat");
        }
        if (tab === "livechat") {
            threadTypes.push("livechat");
        }
        return threadTypes;
    },
});
