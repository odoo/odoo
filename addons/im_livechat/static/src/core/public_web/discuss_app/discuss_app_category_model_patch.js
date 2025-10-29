import { patch } from "@web/core/utils/patch";
import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app/discuss_app_category_model";
import { fields } from "@mail/core/common/record";

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
});
