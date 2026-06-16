import { DiscussNotificationSettings } from "@mail/discuss/core/common/discuss_notification_settings";
import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(DiscussNotificationSettings.prototype, {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.isLiveChatUser = await user.hasGroup("im_livechat.im_livechat_group_user");
        });
    },

    get PUSHNOTIFS() {
        const notifs = super.PUSHNOTIFS;
        if (this.isLiveChatUser) {
            notifs.push({
                label: "livechat_push",
                name: _t("Live Chat"),
                value: this.store.settings.livechat_push,
            });
        }
        return notifs;
    },
});
