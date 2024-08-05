import { patch } from "@web/core/utils/patch";
import { DiscussAppCategory } from "@mail/core/public_web/discuss_app_category_model";
import { Record } from "@mail/core/common/record";
import { compareDatetime } from "@mail/utils/common/misc";

patch(DiscussAppCategory.prototype, {
    setup() {
        super.setup(...arguments);
        this.livechatChannel = Record.one("im_livechat.channel", {
            inverse: "appCategory",
            onDelete() {
                this.delete();
            },
        });
    },
    /**
     * @param {import("models").Thread} t1
     * @param {import("models").Thread} t2
     */
    sortThreads(t1, t2) {
        if (this.livechatChannel || this.eq(this.app?.defaultLivechatCategory)) {
            return compareDatetime(t2.lastInterestDt, t1.lastInterestDt) || t2.id - t1.id;
        }
        return super.sortThreads(t1, t2);
    },
});
