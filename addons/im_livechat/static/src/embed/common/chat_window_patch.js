import { FeedbackPanel } from "@im_livechat/embed/common/feedback_panel/feedback_panel";
import { CloseConfirmation } from "@im_livechat/embed/common/close_confirmation";

import { ChatWindow } from "@mail/core/common/chat_window";

import { toRaw, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { FeedbackPanel, CloseConfirmation });

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.livechatService = useService("im_livechat.livechat");
        this.chatbotService = useService("im_livechat.chatbot");
        this.livechatState = useState({ showCloseConfirmation: false });
    },

    async close() {
        const chatWindow = toRaw(this.props.chatWindow);
        if (chatWindow.thread.id > 0 && !this.livechatState.showCloseConfirmation) {
            this.state.actionsDisabled = true;
            this.livechatState.showCloseConfirmation = true;
        } else {
            this.state.actionsDisabled = false;
            await super.close();
        }
    },

    async onClickNewSession() {
        await this.close();
        await this.livechatService.open();
    },

    onCloseConfirmationDialog() {
        this.state.actionsDisabled = false;
        this.livechatState.showCloseConfirmation = false;
    },
});
