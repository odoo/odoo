import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message_model";

patch(Message.prototype, {
    shouldHideFromMessageListOnDelete(ancestors) {
        return ancestors.projectSharingId || super.shouldHideFromMessageListOnDelete(...arguments);
    },
});
