/** @odoo-module */

import { Messaging, messagingService } from "@mail/new/core/messaging_service";
import { createLocalId } from "@mail/new/utils/misc";
import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, "mail/web", {
    setup(env, services, initialThreadLocalId) {
        this._super(env, services, initialThreadLocalId);
        /** @type {import("@mail/new/chat/chat_window_service").ChatWindow} */
        this.chatWindowService = services["mail.chat_window"];
    },
    initMessagingCallback(data) {
        this.store.user = this.personaService.insert({
            ...data.current_partner,
            type: "partner",
        });
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
        const channel = this.store.threads[createLocalId("mail.channel", notif.payload.id)];
        this.chatWindowService.insert({ thread: channel });
    },
});

patch(messagingService, "mail/web", {
    dependencies: [...messagingService.dependencies, "mail.chat_window"],
});
