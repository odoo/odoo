import { FeedbackPanel } from "@im_livechat/core/common/feedback_panel";

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
        this.props.chatWindow.feedbackDoneResolver.resolve(true);
        await this.livechatService.open();
    },
});
