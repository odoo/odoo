import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message_model";

patch(Message.prototype, {
    get canToggleBookmark() {
        let result = super.canToggleBookmark;
        if (this.thread && this.thread.model !== "discuss.channel") {
            result = result && this.thread.hasReadAccess;
        }
        return result;
    },
    shouldHideFromMessageListOnDelete(env) {
        return env.inFrontendPortalChatter || super.shouldHideFromMessageListOnDelete(...arguments);
    },
});
