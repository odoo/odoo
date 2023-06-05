/** @odoo-module */

import { ChatWindow } from "@mail/chat_window/chat_window";
import { FeedbackPanel } from "../feedback_panel/feedback_panel";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SESSION_STATE } from "../core/livechat_service";
import { useState } from "@odoo/owl";

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
            this.chatWindowService.show(this.props.chatWindow);
        } else {
            this._super();
        }
        this.livechatService.leaveSession();
        this.chatbotService.stop();
    },
});
