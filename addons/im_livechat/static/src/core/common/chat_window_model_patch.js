import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patch } from "@web/core/utils/patch";

export const CW_LIVECHAT_STEP = {
    NONE: undefined,
    CONFIRM_CLOSE: "CONFIRM_CLOSE", // currently showing confirm dialog to close/end livechat
    FEEDBACK: "FEEDBACK", // currently showing feedback panel
};

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.livechatStep = CW_LIVECHAT_STEP.NONE;
    },

    async close(options = {}) {
        if (this.thread?.channel_type !== "livechat") {
            return super.close(...arguments);
        }
        if (options.force) {
            this.livechatStep = CW_LIVECHAT_STEP.CONFIRM_CLOSE;
        }
        const isSelfVisitor = this.thread.livechatVisitorMember?.persona?.eq(this.store.self);
        switch (this.livechatStep) {
            case CW_LIVECHAT_STEP.NONE: {
                if (this.thread.isTransient) {
                    this.thread.delete();
                    super.close(...arguments);
                    break;
                }
                if (!this.thread.livechat_active) {
                    if (isSelfVisitor) {
                        this.livechatStep = CW_LIVECHAT_STEP.FEEDBACK;
                        this.open({ notifyState: this.thread?.state !== "open" });
                    } else {
                        super.close(...arguments);
                    }
                    break;
                }
                this.actionsDisabled = true;
                this.livechatStep = CW_LIVECHAT_STEP.CONFIRM_CLOSE;
                if (!this.hubAsOpened && !options.noLeaveChannel) {
                    this.open();
                }
                break;
            }
            case CW_LIVECHAT_STEP.CONFIRM_CLOSE: {
                this.actionsDisabled = false;
                if (this.thread.livechatVisitorMember?.persona?.eq(this.store.self)) {
                    this.open({ notifyState: this.thread?.state !== "open" });
                    this.livechatStep = CW_LIVECHAT_STEP.FEEDBACK;
                } else {
                    this.livechatStep = CW_LIVECHAT_STEP.NONE;
                    super.close(...arguments);
                }
                break;
            }
            case CW_LIVECHAT_STEP.FEEDBACK: {
                super.close(...arguments);
                break;
            }
        }
        if (this.livechatStep !== CW_LIVECHAT_STEP.CONFIRM_CLOSE) {
            this.store.env.services["im_livechat.livechat"]?.leave();
            this.store.env.services["im_livechat.chatbot"]?.stop();
        }
    },
});
