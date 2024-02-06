/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { DiscussAppCategory } from "@mail/core/common/discuss_app_category_model";
import { compareDatetime } from "@mail/utils/common/misc";
import { Record } from "@mail/core/common/record";

patch(DiscussAppCategory.prototype, {
    setup() {
        this.livechatChannel = Record.one("LivechatChannel");
    },
    /**
     * @param {import("models").Thread} t1
     * @param {import("models").Thread} t2
     */
    sortThreads(t1, t2) {
        if (this.livechatChannel) {
            return (
                compareDatetime(t2.lastInterestDateTime, t1.lastInterestDateTime) || t2.id - t1.id
            );
        }
        return super.sortThreads(t1, t2);
    },
});
