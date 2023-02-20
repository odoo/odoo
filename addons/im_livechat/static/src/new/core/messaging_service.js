/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Messaging } from "@mail/new/core/messaging_service";
import { createLocalId } from "@mail/new/utils/misc";

patch(Messaging.prototype, "im_livechat", {
    initMessagingCallback(data) {
        this._super(data);
        if (data.current_user_settings?.is_discuss_sidebar_category_livechat_open) {
            this.store.discuss.livechat.isOpen = true;
        }
    },

    _handleNotificationLastInterestDtChanged(notif) {
        this._super(notif);
        const channel = this.store.threads[createLocalId("mail.channel", notif.payload.id)];
        if (channel?.type === "livechat") {
            this.threadService.sortChannels();
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
