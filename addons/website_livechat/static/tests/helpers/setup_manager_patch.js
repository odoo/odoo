/* @odoo-module */

import { setupManager } from "@mail/../tests/helpers/webclient_setup";
import { patch } from "@web/core/utils/patch";
import { websiteLivechatNotifications } from "@website_livechat/core/website_livechat_notification_handler";

patch(setupManager, "website_livechat", {
    setupServices() {
        return {
            ...this._super(...arguments),
            "website_livechat.notifications": websiteLivechatNotifications,
        };
    },
});
