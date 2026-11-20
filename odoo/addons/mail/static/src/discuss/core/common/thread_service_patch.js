/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

patch(ThreadService.prototype, {
    /**
     * @override
     * @param {import("models").Thread} thread
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
                await this.executeCommand(thread, command, body);
                return;
            }
        }
        return super.post(...arguments);
    },

    async fetchMoreAttachments(thread, limit = 30) {
        if (thread.isLoadingAttachments || thread.areAttachmentsLoaded) {
            return;
        }
        thread.isLoadingAttachments = true;
        try {
            const rawAttachments = await this.rpc("/discuss/channel/attachments", {
                before: Math.min(...thread.attachments.map(({ id }) => id)),
                channel_id: thread.id,
                limit,
            });
            const attachments = this.store.Attachment.insert(rawAttachments);
            if (attachments.length < limit) {
                thread.areAttachmentsLoaded = true;
            }
        } finally {
            thread.isLoadingAttachments = false;
        }
    },

    async muteThread(thread, { minutes = false } = {}) {
        await this.rpc("/discuss/channel/mute", { channel_id: thread.id, minutes });
    },

    async updateCustomNotifications(thread, custom_notifications) {
        // Update the UI instantly to provide a better UX (no need to wait for the RPC to finish).
        thread.custom_notifications = custom_notifications;
        await this.rpc("/discuss/channel/update_custom_notifications", {
            channel_id: thread.id,
            custom_notifications,
        });
    },
});
