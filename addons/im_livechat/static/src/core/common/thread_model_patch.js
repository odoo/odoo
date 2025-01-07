import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.livechat_operator_id = Record.one("Persona");
    },
    get autoOpenChatWindowOnNewMessage() {
        return this.channel_type === "livechat" || super.autoOpenChatWindowOnNewMessage;
    },
    get showCorrespondentCountry() {
        if (this.channel_type === "livechat") {
            return (
                this.livechat_operator_id?.eq(this.store.self) && Boolean(this.correspondentCountry)
            );
        }
        return super.showCorrespondentCountry;
    },
    get typesAllowingCalls() {
        return super.typesAllowingCalls.concat(["livechat"]);
    },

    get isChatChannel() {
        return this.channel_type === "livechat" || super.isChatChannel;
    },
});
