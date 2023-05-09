/* @odoo-module */

import { registry } from "@web/core/registry";

export const websiteLivechatNotifications = {
    dependencies: ["bus_service", "mail.chat_window", "mail.thread"],
    start(
        env,
        {
            bus_service: busService,
            "mail.chat_window": chatWindowService,
            "mail.thread": threadService,
        }
    ) {
        busService.subscribe("website_livechat.send_chat_request", (payload) => {
            const channel = threadService.insert({
                ...payload,
                id: payload.id,
                model: "discuss.channel",
                serverData: payload,
                type: payload.channel.channel_type,
            });
            const chatWindow = chatWindowService.insert({ thread: channel });
            chatWindowService.makeVisible(chatWindow);
            chatWindowService.focus(chatWindow);
        });
    },
};

registry.category("services").add("website_livechat.notifications", websiteLivechatNotifications);
