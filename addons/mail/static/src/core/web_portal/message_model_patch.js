import { Message } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get canCopyLink() {
        return super.canCopyLink && this.store.self.active !== false;
    },
    canAddReaction(thread) {
        return super.canAddReaction(thread) && this.store.self.active !== false;
    },
});
