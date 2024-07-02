import { MessageReactions } from "@mail/core/common/message_reactions_model";

import { patch } from "@web/core/utils/patch";

patch(MessageReactions.prototype, {
   get removeParams() {
        return {
            ...super.removeParams,
            thread_model: this.message.thread.model,
            thread_id: this.message.thread.id,
            ...this.message.thread.securityParams,
        };
    }
});
