import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.operator = Record.one("Persona");
    },
    get autoOpenChatWindowOnNewMessage() {
        return this.channel_type === "livechat" || super.autoOpenChatWindowOnNewMessage;
    },
    get typesAllowingCalls() {
        return super.typesAllowingCalls.concat(["livechat"]);
    },

    get isChatChannel() {
        return this.channel_type === "livechat" || super.isChatChannel;
    },

    async rename(name) {
        if (this.channel_type === "livechat") {
            const newName = name.trim();
            if (newName && newName !== this.displayName) {
                this.custom_channel_name = newName;
                await this.renameChannel(newName, "channel_set_custom_name");
            }
        } else {
            await super.rename(name);
        }
    },
});
