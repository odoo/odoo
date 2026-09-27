import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message_model";

patch(Message.prototype, {
    shouldHideFromMessageListOnDelete(env) {
        return env.projectSharingId || super.shouldHideFromMessageListOnDelete(...arguments);
    },
});
