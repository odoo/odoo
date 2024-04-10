import { registry } from "@web/core/registry";

export const websiteLivechatNotifications = {
    dependencies: ["bus_service", "mail.store"],
    start(env, { bus_service: busService, "mail.store": store }) {
        busService.subscribe("website_livechat.send_chat_request", (payload) => {
            const channel = store.Thread.insert(payload);
            const chatWindow = store.ChatWindow.insert({ thread: channel });
            chatWindow.makeVisible();
            chatWindow.focus();
        });
    },
};

registry.category("services").add("website_livechat.notifications", websiteLivechatNotifications);
