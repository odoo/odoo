import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    getReactParams(content) {
        return {
            ...super.getReactParams(...arguments),
            thread_model: this.thread.model,
            thread_id: this.thread.id,
            ...this.thread.securityParams,
        };
    }
});
