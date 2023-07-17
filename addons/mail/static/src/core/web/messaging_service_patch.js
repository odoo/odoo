/* @odoo-module */

import { Messaging, messagingService } from "@mail/core/common/messaging_service";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";

patch(Messaging.prototype, "mail/core/web", {
    setup(env, services, initialThreadLocalId) {
        this._super(env, services, initialThreadLocalId);
        /** @type {import("@mail/core/common/chat_window_service").ChatWindow} */
        this.chatWindowService = services["mail.chat_window"];
        this.notificationService = services.notification;
        this.ui = services["ui"];
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
});

patch(messagingService, "mail/core/web", {
    dependencies: [...messagingService.dependencies, "mail.chat_window", "notification", "ui"],
});
