/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;

export const newMessageService = {
    dependencies: ["command"],
    start(newEnv, { command }) {
        command.add("Message a user", async () => {
            const env = Component.env;
            await env.messagingCreatedPromise;
            await env.messaging.initializedPromise;
            if (env.messaging.discuss.isOpen) {
                env.messaging.discuss.update({
                    isAddingChannel: false,
                    isAddingChat: true,
                });
            } else {
                env.messaging.chatWindowManager.openNewMessage();
            }
        }, {
            category: "mail",
            hotkey: "alt+shift+w",
        });
    },
};

registry.category("services").add("new_message", newMessageService);
