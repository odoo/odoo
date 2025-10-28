import { DiscussNotificationSettings } from "@mail/discuss/core/common/discuss_notification_settings";
import { onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(DiscussNotificationSettings.prototype, {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.isLiveChatUser = await user.hasGroup("im_livechat.im_livechat_group_user");
        });
    },
});
