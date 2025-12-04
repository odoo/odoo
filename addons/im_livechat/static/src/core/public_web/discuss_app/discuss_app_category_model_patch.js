import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app/discuss_app_category_model";
import { fields } from "@mail/model/export";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

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
    sortThreads(t1, t2) {
        if (this.eq(this.store.discuss?.livechatLookingForHelpCategory)) {
            return compareDatetime(t1.lastInterestDt, t2.lastInterestDt) || t1.id - t2.id;
        }
        return super.sortThreads(...arguments);
    },
});
