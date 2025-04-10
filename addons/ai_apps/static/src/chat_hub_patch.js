import { patch } from "@web/core/utils/patch";
import { ChatHub } from "@mail/core/common/chat_hub";

patch(ChatHub.prototype, {
    get displayChatHub() {
        return (
            super.displayChatHub || 
            this.store.aiInsertButtonTarget
        );
    },
});