import { patch } from "@web/core/utils/patch";
import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app_category_model";
import { fields } from "@mail/core/common/record";
import { compareDatetime } from "@mail/utils/common/misc";

patch(DiscussAppCategory.prototype, {
    setup() {
        super.setup(...arguments);
        this.livechat_channel_id = fields.One("im_livechat.channel", {
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
        if (this.eq(this.app?.livechatLookingForHelpCategory)) {
            return t1.id - t2.id;
        }
        if (this.livechat_channel_id || this.eq(this.app?.defaultLivechatCategory)) {
            return compareDatetime(t2.lastInterestDt, t1.lastInterestDt) || t2.id - t1.id;
        }
        return super.sortThreads(t1, t2);
    },
});
