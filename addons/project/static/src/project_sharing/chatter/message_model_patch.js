import { Message } from "@mail/core/common/message_model";
import { patchModel } from "@mail/model/export";

export const messagePatch = patchModel(Message, {
    shouldHideFromMessageListOnDelete(env) {
        return env.projectSharingId || super.shouldHideFromMessageListOnDelete(...arguments);
    },
});
