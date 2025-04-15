/* @odoo-module */

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class DiscussCoreWeb {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.notificationService = services.notification;
        this.ui = services.ui;
        this.chatWindowService = services["mail.chat_window"];
        this.discussCoreCommonService = services["discuss.core.common"];
        this.messagingService = services["mail.messaging"];
        this.store = services["mail.store"];
        this.threadService = services["mail.thread"];
    }

    setup() {
        this.messagingService.isReady.then((data) => {
            this.store.discuss.channels.isOpen =
                data.current_user_settings.is_discuss_sidebar_category_channel_open;
            this.store.discuss.chats.isOpen =
                data.current_user_settings.is_discuss_sidebar_category_chat_open;
            this.busService.start();
        });
        this.env.bus.addEventListener(
            "discuss.channel/new_message",
            ({ detail: { channel, message } }) => {
                if (this.ui.isSmall || message.isSelfAuthored) {
                    return;
                }
                if (channel.correspondent?.eq(this.store.odoobot) && this.store.odoobotOnboarding) {
                    // this cancels odoobot onboarding auto-opening of chat window
                    this.store.odoobotOnboarding = false;
                    return;
                }
                this.threadService.notifyMessageToUser(channel, message);
            }
        );
        this.busService.subscribe("res.users.settings", (payload) => {
            if (payload) {
                this.store.discuss.chats.isOpen =
                    payload.is_discuss_sidebar_category_chat_open ??
                    this.store.discuss.chats.isOpen;
                this.store.discuss.channels.isOpen =
                    payload.is_discuss_sidebar_category_channel_open ??
                    this.store.discuss.channels.isOpen;
            }
        });
        this.busService.subscribe("res.users/connection", async ({ partnerId, username }) => {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            const notification = _t(
                "%(user)s connected. This is their first connection. Wish them luck.",
                { user: username }
            );
            this.notificationService.add(notification, { type: "info" });
            const chat = await this.threadService.getChat({ partnerId });
            if (chat && !this.ui.isSmall) {
                this.store.ChatWindow.insert({ thread: chat });
            }
        });
        this.busService.subscribe("discuss.Thread/fold_state", (data) => {
            const thread = this.store.Thread.get(data);
            if (data.fold_state && thread && data.foldStateCount > thread.foldStateCount) {
                thread.foldStateCount = data.foldStateCount;
                if (data.fold_state !== thread.state) {
                    thread.state = data.fold_state;
                    if (thread.state === "closed") {
                        const chatWindow = this.store.discuss.chatWindows.find((chatWindow) =>
                            chatWindow.thread?.eq(thread)
                        );
                        if (chatWindow) {
                            this.chatWindowService.close(chatWindow, { notifyState: false });
                        }
                    } else {
                        this.store.ChatWindow.insert({
                            thread,
                            folded: thread.state === "folded",
                        });
                    }
                }
            }
        });
    }
}

export const discussCoreWeb = {
    dependencies: [
        "bus_service",
        "discuss.core.common",
        "mail.chat_window",
        "mail.messaging",
        "mail.store",
        "mail.thread",
        "notification",
        "ui",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const discussCoreWeb = reactive(new DiscussCoreWeb(env, services));
        discussCoreWeb.setup();
        return discussCoreWeb;
    },
};

registry.category("services").add("discuss.core.web", discussCoreWeb);
