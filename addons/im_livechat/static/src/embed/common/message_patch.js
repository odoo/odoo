import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

Message.props.push("isTypingMessage?");

patch(Message.prototype, {
    setup() {
        super.setup();
        this.url = url;
    },

    get quickActionCount() {
        return this.props.thread?.channel_type === "livechat" ? 3 : super.quickActionCount;
    },

    /**
     * @param {import("@im_livechat/embed/common/chatbot/chatbot_step_model").StepAnswer} answer
     */
    answerChatbot(answer) {
        return this.props.message.thread.post(answer.name, {}, { selected_answer_id: answer.id });
    },
});
