/* @odoo-module */

import { registry } from "@web/core/registry";

export const websiteLivechatNotifications = {
    dependencies: ["bus_service", "mail.chat_window", "mail.store"],
    start(
        env,
        { bus_service: busService, "mail.chat_window": chatWindowService, "mail.store": store }
    ) {
        busService.subscribe("website_livechat.send_chat_request", (payload) => {
            const channel = store.Thread.insert({
                ...payload,
                id: payload.id,
                model: "discuss.channel",
                type: payload.channel_type,
            });
            const chatWindow = store.ChatWindow.insert({ thread: channel });
            chatWindowService.makeVisible(chatWindow);
            chatWindowService.focus(chatWindow);
        });
    },
};

registry.category("services").add("website_livechat.notifications", websiteLivechatNotifications);
