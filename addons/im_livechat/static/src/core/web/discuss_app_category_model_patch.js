/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { DiscussAppCategory } from "@mail/core/common/discuss_app_category_model";
import { Record } from "@mail/core/common/record";
import { compareDatetime } from "@mail/utils/common/misc";

patch(DiscussAppCategory.prototype, {
    setup() {
        super.setup(...arguments);
        this.livechatChannel = Record.one("LivechatChannel", { inverse: "appCategory" });
    },
    /**
     * @param {import("models").Thread} t1
     * @param {import("models").Thread} t2
     */
    sortThreads(t1, t2) {
        if (this.isLivechatCategory) {
            return (
                compareDatetime(t2.lastInterestDateTime, t1.lastInterestDateTime) || t2.id - t1.id
            );
        }
        return super.sortThreads(t1, t2);
    },

    get isLivechatCategory() {
        return this.livechatChannel || this.eq(this.app?.defaultLivechatCategory);
    },
});

patch(DiscussAppCategory, {
    LIVECHAT_SEQUENCE: 20,
    insert() {
        const category = super.insert(...arguments);
        if (category.isLivechatCategory) {
            category._store.settings[category.openStateKey] ??= true;
        }
        return category;
    },
});
