/* @odoo-module */

import { Messaging } from "@mail/core/common/messaging_service";

import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, "im_livechat", {
    initMessagingCallback(data) {
        this._super(data);
        if (data.current_user_settings?.is_discuss_sidebar_category_livechat_open) {
            this.store.discuss.livechat.isOpen = true;
        }
    },
    _handleNotificationRecordInsert(notif) {
        this._super(notif);
        const { "res.users.settings": settings } = notif.payload;
        if (settings) {
            this.store.discuss.livechat.isOpen =
                settings.is_discuss_sidebar_category_livechat_open ??
                this.store.discuss.livechat.isOpen;
        }
    },
});
