import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";
import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    setup() {
        super.setup();
        this.hasFeedbackPanel = false;
    },
    async close() {
        if (this.thread?.channel_type !== "livechat") {
            return super.close(...arguments);
        }
        if (this.store.env.services["im_livechat.livechat"].state === SESSION_STATE.PERSISTED) {
            this.hasFeedbackPanel = true;
            this.open({ notifyState: this.thread?.state !== "open" });
        } else {
            await super.close(...arguments);
            if (this.thread.isTransient) {
                this.thread.delete();
            }
        }
        this.store.env.services["im_livechat.livechat"].leave();
        this.store.env.services["im_livechat.chatbot"].stop();
    },
});
