import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app/discuss_app_category_model";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

patch(DiscussAppCategory.prototype, {
    sortChannels(c1, c2) {
        if (this.eq(this.store.discuss?.livechatLookingForHelpCategory)) {
            return (
                compareDatetime(
                    c1.livechat_looking_for_help_since_dt,
                    c2.livechat_looking_for_help_since_dt
                ) || c1.id - c2.id
            );
        }
        return super.sortChannels(...arguments);
    },
});
