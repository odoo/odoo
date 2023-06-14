/* @odoo-module */

import { SESSION_STATE } from "@im_livechat/embed/core/livechat_service";
import { FeedbackPanel } from "@im_livechat/embed/feedback_panel/feedback_panel";

import { ChatWindow } from "@mail/core/common/chat_window";
import { showChatWindow } from "@mail/core/common/chat_window_service";

import { useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { FeedbackPanel });

patch(ChatWindow.prototype, "im_livechat", {
    setup() {
        this._super(...arguments);
        this.livechatService = useService("im_livechat.livechat");
        this.chatbotService = useState(useService("im_livechat.chatbot"));
        this.livechatState = useState({
            hasFeedbackPanel: false,
        });
    },

    close() {
        if (this.thread?.type !== "livechat") {
            return this._super();
        }
        if (this.livechatService.state === SESSION_STATE.PERSISTED) {
            this.livechatState.hasFeedbackPanel = true;
            showChatWindow(this.props.chatWindow);
        } else {
            this._super();
        }
        this.livechatService.leaveSession();
        this.chatbotService.stop();
    },
});
