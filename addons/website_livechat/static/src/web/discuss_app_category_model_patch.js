/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { DiscussAppCategory } from "@mail/core/common/discuss_app_category_model";

patch(DiscussAppCategory.prototype, {
    /**
     * @param {import("models").Thread} t1
     * @param {import("models").Thread} t2
     */
    sortThreads(t1, t2) {
        if (this.id === "livechat") {
            return t2.lastInterestDateTime?.ts - t1.lastInterestDateTime?.ts;
        }
        return super.sortThreads(t1, t2);
    },
});
