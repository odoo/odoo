/* @odoo-module */

import { ThreadService } from "@mail/core/thread_service";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

patch(ThreadService.prototype, "discuss", {
    /**
     * @override
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {string} body
     */
    async post(thread, body) {
        if (thread.model === "discuss.channel" && body.startsWith("/")) {
            const [firstWord] = body.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                command &&
                (!command.channel_types || command.channel_types.includes(thread.type))
            ) {
                await thread.executeCommand(command, body);
                return;
            }
        }
        return this._super(...arguments);
    },
});
