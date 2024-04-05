import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";
import { FeedbackPanel } from "@im_livechat/embed/common/feedback_panel/feedback_panel";

import { ChatWindow } from "@mail/core/common/chat_window";

import { useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { FeedbackPanel });

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.livechatService = useService("im_livechat.livechat");
        this.chatbotService = useState(useService("im_livechat.chatbot"));
        this.livechatState = useState({ hasFeedbackPanel: false });
    },

    async close() {
        if (this.thread?.channel_type !== "livechat") {
            return super.close();
        }
        if (this.livechatService.state === SESSION_STATE.PERSISTED) {
            this.livechatState.hasFeedbackPanel = true;
            this.props.chatWindow.show({ notifyState: false });
        } else {
            this.thread?.delete();
            await super.close();
        }
        this.livechatService.leave();
        this.chatbotService.stop();
    },
});
