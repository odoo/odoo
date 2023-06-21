/* @odoo-module */

import {
    Messaging,
    initMessagingCallback,
    loadFailures,
    messagingService,
    _handleNotificationNewMessage,
} from "@mail/core/common/messaging_service";
import { createLocalId } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";
import { createChannelThread, getChat } from "../common/thread_service";
import { patchFn } from "@mail/utils/common/patch";
import { insertChatWindow } from "@mail/core/common/chat_window_service";

let notificationService;
let ui;
/** @type {import("@mail/core/common/store_service").Store} */
let store;

patchFn(initMessagingCallback, function (data) {
    loadFailures();
    for (const channelData of data.channels) {
        const thread = createChannelThread(channelData);
        if (channelData.is_minimized && channelData.state !== "closed") {
            insertChatWindow({
                autofocus: 0,
                folded: channelData.state === "folded",
                thread,
            });
        }
    }
    this._super(data);
});

patchFn(_handleNotificationNewMessage, async function (notif) {
    await this._super(notif);
    const channel = store.threads[createLocalId("discuss.channel", notif.payload.id)];
    const message = store.messages[notif.payload.message.id];
    if (!ui.isSmall && channel.correspondent !== store.odoobot && !message.isSelfAuthored) {
        insertChatWindow({ thread: channel });
    }
});

patch(Messaging.prototype, "mail/core/web", {
    setup(env, services, initialThreadLocalId) {
        this._super(env, services, initialThreadLocalId);
        store = services["mail.store"];
        ui = services["ui"];
        notificationService = services.notification;
        this.bus.subscribe("res.users/connection", async ({ partnerId, username }) => {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            const notification = sprintf(
                _t("%(user)s connected. This is their first connection. Wish them luck."),
                { user: username }
            );
            notificationService.add(notification, { type: "info" });
            const chat = await getChat({ partnerId });
            if (chat) {
                insertChatWindow({ thread: chat });
            }
        });
    },
});

patch(messagingService, "mail/core/web", {
    dependencies: [...messagingService.dependencies, "mail.chat_window", "ui"],
});
