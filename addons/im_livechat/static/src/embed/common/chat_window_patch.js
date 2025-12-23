import { FeedbackPanel } from "@im_livechat/embed/common/feedback_panel/feedback_panel";

import { ChatWindow } from "@mail/core/common/chat_window";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { FeedbackPanel });

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.livechatService = useService("im_livechat.livechat");
    },
    async onClickNewSession() {
        this.props.chatWindow.feedbackDoneResolver.resolve();
        await this.livechatService.open();
    },
    get showGiveFeedbackBtn() {
        if (this.channel.channel_type !== "livechat") {
            return false;
        }
        return this.channel.chatbot?.completed || this.channel.livechat_end_dt;
    },
});
