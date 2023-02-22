/** @odoo-module */

import { Messaging } from "@mail/new/core/messaging_service";
import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, "website_livechat", {
    handleNotification(notifications) {
        this._super(notifications);
        for (const notification of notifications) {
            if (notification.type === "website_livechat.send_chat_request") {
                const channel = this.threadService.insert({
                    ...notification.payload,
                    id: notification.payload.id,
                    model: "mail.channel",
                    serverData: notification.payload,
                    type: notification.payload.channel_type,
                });
                const chatWindow = this.chatWindowService.insert({ thread: channel });
                this.chatWindowService.makeVisible(chatWindow);
                this.chatWindowService.focus(chatWindow);
            }
        }
    },
});
