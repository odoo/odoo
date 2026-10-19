import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get bubbleColor() {
        if (this.thread?.ratingChatter) {
            return undefined;
        }
        return super.bubbleColor;
    },

    shouldHideFromMessageListOnDelete(_env) {
        if (this.thread?.ratingChatter && this.rating_value !== null) {
            return true;
        }
        return super.shouldHideFromMessageListOnDelete(...arguments);
    },

    async remove(options = {}) {
        if (this.thread?.ratingChatter && this.rating_value !== null) {
            const { thread } = this;
            const data = await super.remove({ ...options, removeFromThread: false });
            this.store.env.bus.trigger("MAIL:RELOAD-THREAD", {
                model: thread.model,
                id: thread.id,
            });
            return data;
        }
        return super.remove(options);
    },
});
