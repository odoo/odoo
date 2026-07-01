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
        if (this.thread?.ratingChatter && this.rating_value != null) {
            return true;
        }
        return super.shouldHideFromMessageListOnDelete(...arguments);
    },

    async remove() {
        if (this.thread?.ratingChatter && this.rating_value != null) {
            const data = await super.remove({ removeFromThread: false });
            await this.thread._reloadReviews?.();
            return data;
        }
        return super.remove(...arguments);
    },
});
