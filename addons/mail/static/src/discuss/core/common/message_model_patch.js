import { Message } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    /** @type {Promise[]} */
    mentionedChannelPromises: [],
});
