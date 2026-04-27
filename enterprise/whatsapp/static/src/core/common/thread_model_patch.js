import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";

import { toRaw } from "@odoo/owl";

patch(Thread.prototype, {
    get importantCounter() {
        if (this.channel_type === "whatsapp") {
            return this.selfMember?.message_unread_counter || this.message_needaction_counter;
        }
        return super.importantCounter;
    },
    get autoOpenChatWindowOnNewMessage() {
        return this.channel_type === "whatsapp" || super.autoOpenChatWindowOnNewMessage;
    },
    get canLeave() {
        return this.channel_type !== "whatsapp" && super.canLeave;
    },
    get canUnpin() {
        if (this.channel_type === "whatsapp") {
            return this.importantCounter === 0;
        }
        return super.canUnpin;
    },

    get avatarUrl() {
        if (this.channel_type === "whatsapp" && this.correspondent) {
            return this.correspondent.persona.avatarUrl;
        }
        return super.avatarUrl;
    },

    get isChatChannel() {
        return this.channel_type === "whatsapp" || super.isChatChannel;
    },

    get whatsappChannelValidUntilDatetime() {
        if (!this.whatsapp_channel_valid_until) {
            return undefined;
        }
        return toRaw(deserializeDateTime(this.whatsapp_channel_valid_until));
    },
});
