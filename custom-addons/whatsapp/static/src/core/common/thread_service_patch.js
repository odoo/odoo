/** @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";
import { compareDatetime } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    canLeave(thread) {
        return thread.type !== "whatsapp" && super.canLeave(thread);
    },

    canUnpin(thread) {
        if (thread.type === "whatsapp") {
            return this.getCounter(thread) === 0;
        }
        return super.canUnpin(thread);
    },

    getCounter(thread) {
        if (thread.type === "whatsapp") {
            return thread.message_unread_counter || thread.message_needaction_counter;
        }
        return super.getCounter(thread);
    },

    async getMessagePostParams({ thread }) {
        const params = await super.getMessagePostParams(...arguments);

        if (thread.type === "whatsapp") {
            params.post_data.message_type = "whatsapp_message";
        }
        return params;
    },

    async openWhatsAppChannel(id, name) {
        const thread = this.store.Thread.insert({
            id,
            model: "discuss.channel",
            name,
            type: "whatsapp",
            channel: { avatarCacheKey: "hello" },
        });
        if (!thread.hasSelfAsMember) {
            const data = await this.orm.call("discuss.channel", "whatsapp_channel_join_and_pin", [
                [id],
            ]);
            thread.update(data);
        } else if (!thread.is_pinned) {
            this.pin(thread);
        }
        this.open(thread);
    },

    /** @deprecated */
    sortChannels() {
        super.sortChannels();
        // WhatsApp Channels are sorted by most recent interest date time in the sidebar.
        this.store.discuss.whatsapp.threads.sort(
            (t1, t2) =>
                compareDatetime(t2.lastInterestDateTime, t1.lastInterestDateTime) || t2.id - t1.id
        );
    },
});
