/* @odoo-module */

import { executeChannelCommand, postMessage } from "@mail/core/common/thread_service";
import { patchFn } from "@mail/utils/common/patch";

import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

/**
 * @override
 * @param {import("@mail/core/common/thread_model").Thread} thread
 * @param {string} body
 */
patchFn(postMessage, async function (thread, body) {
    if (thread.model === "discuss.channel" && body.startsWith("/")) {
        const [firstWord] = body.substring(1).split(/\s/);
        const command = commandRegistry.get(firstWord, false);
        if (command && (!command.channel_types || command.channel_types.includes(thread.type))) {
            await executeChannelCommand(thread, command, body);
            return;
        }
    }
    return this._super(...arguments);
});
