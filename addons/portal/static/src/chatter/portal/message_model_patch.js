import { Message } from "@mail/core/common/message_model";
import { patchModel } from "@mail/model/export";

export const messagePatch = patchModel(Message, {
    get canToggleBookmark() {
        let result = super.canToggleBookmark;
        if (this.thread && !this.thread.channel) {
            result = result && this.thread.hasReadAccess;
        }
        return result;
    },
    shouldHideFromMessageListOnDelete(env, ancestors) {
        return (
            ancestors.inFrontendPortalChatter ||
            super.shouldHideFromMessageListOnDelete(...arguments)
        );
    },
});
