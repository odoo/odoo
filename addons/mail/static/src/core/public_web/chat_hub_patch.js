import { patch } from "@web/core/utils/patch";
import { ChatHub } from "@mail/core/common/chat_hub";

patch(ChatHub.prototype, {
    get isShown() {
        return super.isShown && !this.store.discuss.isActive;
    },
});
