import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";
import { FeedbackPanel } from "@im_livechat/embed/common/feedback_panel/feedback_panel";
import { CloseConfirmation } from "@im_livechat/embed/common/close_confirmation";

import { ChatWindow } from "@mail/core/common/chat_window";

import { useState, toRaw } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { FeedbackPanel, CloseConfirmation });

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.livechatService = useService("im_livechat.livechat");
        this.chatbotService = useState(useService("im_livechat.chatbot"));
        this.closeFeedback = false;
        this.livechatState = useState({
            hasFeedbackPanel: false,
            showCloseConfirmation: false,
        });
    },

    async close() {
        if (this.thread?.channel_type !== "livechat") {
            return super.close();
        }
        const chatWindow = toRaw(this.props.chatWindow);
        if (chatWindow.folded) {
            this.props.chatWindow.show({ notifyState: this.thread?.state !== "open" });
        }
        this.livechatState.showCloseConfirmation = true;
        if (this.closeFeedback) {
            await this.closeChatWindow();
        }
    },

    async closeChatWindow() {
        await super.close();
    },

    async onClickLeaveConversation() {
        if (this.livechatService.state === SESSION_STATE.PERSISTED) {
            this.livechatState.hasFeedbackPanel = true;
            this.props.chatWindow.show({ notifyState: this.thread?.state !== "open" });
            this.closeFeedback = true;
        } else {
            await this.closeChatWindow();
        }
        this.livechatService.leave();
        this.chatbotService.stop();
    },

    onCloseConfirmationDialog() {
        this.livechatState.showCloseConfirmation = false;
    },
});
