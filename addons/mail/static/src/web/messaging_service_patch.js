/** @odoo-module */

import { Messaging, messagingService } from "@mail/core/messaging_service";
import { createLocalId } from "@mail/utils/misc";
import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, "mail/web", {
    setup(env, services, initialThreadLocalId) {
        this._super(env, services, initialThreadLocalId);
        /** @type {import("@mail/chat/chat_window_service").ChatWindow} */
        this.chatWindowService = services["mail.chat_window"];
        this.ui = services["ui"];
    },
    initMessagingCallback(data) {
        this.loadFailures();
        for (const channelData of data.channels) {
            const thread = this.threadService.createChannelThread(channelData);
            if (channelData.is_minimized && channelData.state !== "closed") {
                this.chatWindowService.insert({
                    autofocus: 0,
                    folded: channelData.state === "folded",
                    thread,
                });
            }
        }
        this._super(data);
    },
    async _handleNotificationNewMessage(notif) {
        await this._super(notif);
        const channel = this.store.threads[createLocalId("discuss.channel", notif.payload.id)];
        const message = this.store.messages[notif.payload.message.id];
        if (
            !this.ui.isSmall &&
            channel.correspondent !== this.store.odoobot &&
            !message.isSelfAuthored
        ) {
            this.chatWindowService.insert({ thread: channel });
        }
    },
});

patch(messagingService, "mail/web", {
    dependencies: [...messagingService.dependencies, "mail.chat_window", "ui"],
});
