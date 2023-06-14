/* @odoo-module */

import {
    focusChatWindow,
    insertChatWindow,
    makeChatWindowVisible,
} from "@mail/core/common/chat_window_service";
import { insertThread } from "@mail/core/common/thread_service";
import { registry } from "@web/core/registry";

export const websiteLivechatNotifications = {
    dependencies: ["bus_service", "mail.chat_window"],
    start(env, { bus_service: busService, "mail.chat_window": chatWindowService }) {
        busService.subscribe("website_livechat.send_chat_request", (payload) => {
            const channel = insertThread({
                ...payload,
                id: payload.id,
                model: "discuss.channel",
                type: payload.channel.channel_type,
            });
            const chatWindow = insertChatWindow({ thread: channel });
            makeChatWindowVisible(chatWindow);
            focusChatWindow(chatWindow);
        });
    },
};

registry.category("services").add("website_livechat.notifications", websiteLivechatNotifications);
