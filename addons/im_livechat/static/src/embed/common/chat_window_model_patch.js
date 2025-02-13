import { patch } from "@web/core/utils/patch";
import { ChatWindow } from "@mail/core/common/chat_window_model";
import { CW_LIVECHAT_STEP } from "@im_livechat/core/common/chat_window_model_patch";

patch(ChatWindow.prototype, {
    close() {
        super.close(...arguments);
        if (this.livechatStep === CW_LIVECHAT_STEP.FEEDBACK) {
            this.store.env.services["im_livechat.livechat"].leave(this.thread);
            this.thread.chatbot?.stop();
        }
    },
});
