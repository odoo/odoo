/** @odoo-module */

import { Messaging, messagingService } from "@mail/new/core/messaging_service";
import { session } from "@web/session";
import { createLocalId } from "@mail/new/utils/misc";
import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, "mail/web", {
    setup(env, services, initialThreadLocalId) {
        this._super(env, services, initialThreadLocalId);
        /** @type {import("@mail/new/chat/chat_window_service").ChatWindow} */
        this.chatWindowService = services["mail.chat_window"];
    },
    initMessagingCallback(data) {
        if (data.current_partner) {
            this.store.user = this.personaService.insert({
                ...data.current_partner,
                type: "partner",
            });
        }
        if (data.currentGuest) {
            this.store.guest = this.personaService.insert({
                ...data.currentGuest,
                type: "guest",
                channelId: data.channels[0]?.id,
            });
        }
        if (session.user_context.uid) {
            this.loadFailures();
        }
        this.store.partnerRoot = this.personaService.insert({
            ...data.partner_root,
            type: "partner",
        });
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
        this.threadService.sortChannels();
        const settings = data.current_user_settings;
        this.userSettingsService.updateFromCommands(settings);
        this.userSettingsService.id = settings.id;
        this.store.companyName = data.companyName;
        this.store.discuss.channels.isOpen = settings.is_discuss_sidebar_category_channel_open;
        this.store.discuss.chats.isOpen = settings.is_discuss_sidebar_category_chat_open;
        this.store.discuss.inbox.counter = data.needaction_inbox_counter;
        this.store.internalUserGroupId = data.internalUserGroupId;
        this.store.discuss.starred.counter = data.starred_counter;
        (data.shortcodes ?? []).forEach((code) => {
            this.insertCannedResponse(code);
        });
        this.isReady.resolve();
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
