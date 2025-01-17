import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patch } from "@web/core/utils/patch";

export const CW_LIVECHAT_STEP = {
    NONE: undefined,
    CONFIRM_CLOSE: "CONFIRM_CLOSE", // currently showing confirm dialog to close/end livechat
    FEEDBACK: "FEEDBACK", // currently showing feedback panel
};

/** @type {import("models").ChatWindow} */
const chatWindowPatch = {
    setup() {
        super.setup(...arguments);
        this.livechatStep = CW_LIVECHAT_STEP.NONE;
    },
    close(...args) {
        if (this.thread?.channel_type !== "livechat") {
            return super.close(...args);
        }
        const isSelfVisitor = this.thread.livechatVisitorMember?.persona?.eq(this.store.self);
        switch (this.livechatStep) {
            case CW_LIVECHAT_STEP.NONE: {
                if (this.thread.isTransient) {
                    this.thread.delete();
                    super.close(...args);
                    break;
                }
                if (!this.thread.livechat_active) {
                    if (isSelfVisitor) {
                        this.livechatStep = CW_LIVECHAT_STEP.FEEDBACK;
                        this.open({ notifyState: this.thread?.state !== "open" });
                    } else {
                        super.close(...args);
                    }
                    break;
                }
                this.actionsDisabled = true;
                this.livechatStep = CW_LIVECHAT_STEP.CONFIRM_CLOSE;
                if (!this.hubAsOpened) {
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
                    super.close(...args);
                }
                break;
            }
            case CW_LIVECHAT_STEP.FEEDBACK: {
                super.close(...args);
                break;
            }
        }
        if (this.livechatStep !== CW_LIVECHAT_STEP.CONFIRM_CLOSE) {
            this.store.env.services["im_livechat.livechat"]?.leave();
            this.store.env.services["im_livechat.chatbot"]?.stop();
        }
    },
    _onClose() {
        if (
            this.thread?.channel_type === "livechat" &&
            this.thread.livechatVisitorMember?.persona?.notEq(this.store.self)
        ) {
            const thread = this.thread; // save ref before delete
            super._onClose();
            this.delete();
            thread.leaveChannel({ force: true });
        } else {
            super._onClose();
        }
    },
};
patch(ChatWindow.prototype, chatWindowPatch);
