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
