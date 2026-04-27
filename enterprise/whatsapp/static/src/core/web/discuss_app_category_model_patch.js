/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { DiscussAppCategory } from "@mail/core/public_web/discuss_app_category_model";
import { compareDatetime } from "@mail/utils/common/misc";

patch(DiscussAppCategory.prototype, {
    /**
     * @param {import("models").Thread} t1
     * @param {import("models").Thread} t2
     */
    sortThreads(t1, t2) {
        if (this.id === "whatsapp") {
            return compareDatetime(t2.lastInterestDt, t1.lastInterestDt) || t2.id - t1.id;
        }
        return super.sortThreads(t1, t2);
    },
});
