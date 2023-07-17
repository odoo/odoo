/* @odoo-module */

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";

export class DiscussCoreWeb {
    constructor(env, services) {
        Object.assign(this, {
            busService: services.bus_service,
            env,
            notificationService: services.notification,
            ui: services.ui,
        });
        /** @type {import("@mail/core/common/chat_window_service").ChatWindowService} */
        this.chatWindowService = services["mail.chat_window"];
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        this.messagingService = services["mail.messaging"];
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = services["mail.thread"];
    }

    setup() {
        this.messagingService.isReady.then((data) => {
            for (const channelData of data.channels) {
                const thread = this.threadService.createChannelThread(channelData);
                if (
                    channelData.is_minimized &&
                    channelData.state !== "closed" &&
                    !this.ui.isSmall
                ) {
                    this.chatWindowService.insert({
                        autofocus: 0,
                        folded: channelData.state === "folded",
                        thread,
                    });
                }
            }
            this.store.discuss.channels.isOpen =
                data.current_user_settings.is_discuss_sidebar_category_channel_open;
            this.store.discuss.chats.isOpen =
                data.current_user_settings.is_discuss_sidebar_category_chat_open;
        });
        this.env.bus.addEventListener(
            "discuss.channel/new_message",
            ({ detail: { channel, message } }) => {
                if (
                    !this.ui.isSmall &&
                    channel.correspondent !== this.store.odoobot &&
                    !message.isSelfAuthored
                ) {
                    this.chatWindowService.insert({ thread: channel });
                }
            }
        );
        this.busService.subscribe("res.users/connection", async ({ partnerId, username }) => {
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
    }
}

export const discussCoreWeb = {
    dependencies: [
        "bus_service",
        "mail.chat_window",
        "mail.messaging",
        "mail.store",
        "mail.thread",
        "notification",
        "ui",
    ],
    start(env, services) {
        const discussCoreWeb = reactive(new DiscussCoreWeb(env, services));
        discussCoreWeb.setup();
        return discussCoreWeb;
    },
};

registry.category("services").add("discuss.core.web", discussCoreWeb);
