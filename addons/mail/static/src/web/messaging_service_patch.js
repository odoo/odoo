/** @odoo-module */

import { Messaging, messagingService } from "@mail/core/messaging_service";
import { createLocalId } from "@mail/utils/misc";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";

patch(Messaging.prototype, "mail/web", {
    setup(env, services, initialThreadLocalId) {
        this._super(env, services, initialThreadLocalId);
        /** @type {import("@mail/chat/chat_window_service").ChatWindow} */
        this.chatWindowService = services["mail.chat_window"];
        this.ui = services.ui;
        this.bus.subscribe("res.users/connection", async ({ partnerId, username }) => {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            const notification = sprintf(
                _t("%(user)s connected. This is their first connection. Wish them luck."),
                { user: username }
            );
            this.notificationService.add(notification, { type: "info" });
            const chat = await this.threadService.getChat({ partnerId });
            if (chat && !this.ui.isSmall) {
                this.chatWindowService.insert({ thread: chat });
            }
        });
    },
    initMessagingCallback(data) {
        this.loadFailures();
        for (const channelData of data.channels) {
            const thread = this.threadService.createChannelThread(channelData);
            if (channelData.is_minimized && channelData.state !== "closed" && !this.ui.isSmall) {
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
            !this.store.isSmall &&
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
