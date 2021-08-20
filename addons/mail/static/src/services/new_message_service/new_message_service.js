/** @odoo-module **/

import { registry } from "@web/core/registry";

export const newMessageService = {
    dependencies: ["command", "messaging"],
    start(env, { command }) {
        command.add("Message a user", async () => {
            const messaging = await env.services.messaging.get();
            if (messaging.discuss.isOpen) {
                messaging.discuss.update({
                    isAddingChannel: false,
                    isAddingChat: true,
                });
            } else {
                messaging.chatWindowManager.openNewMessage();
            }
        }, {
            category: "mail",
            hotkey: "alt+shift+w",
        });
    },
};

registry.category("services").add("new_message", newMessageService);
