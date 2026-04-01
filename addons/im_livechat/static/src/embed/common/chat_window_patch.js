import { CW_LIVECHAT_STEP } from "@im_livechat/core/common/chat_window_model_patch";
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
        this.livechatState = useState({ showCloseConfirmation: false });
    },
    async onClickNewSession() {
        await this.close();
        await this.livechatService.open();
    },
    onClickFeedback() {
        this.props.chatWindow.livechatStep = CW_LIVECHAT_STEP.CONFIRM_CLOSE; // Skip the confirmation step.
        this.close();
    },
    get showGiveFeedbackBtn() {
        const thread = this.props.chatWindow.thread;
        if (thread?.channel_type !== "livechat") {
            return false;
        }
        return thread.chatbot?.completed || thread.livechat_end_dt;
    },
});
