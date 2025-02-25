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
     * @param {import("@im_livechat/core/common/chatbot_step_model").StepAnswer} answer
     */
    answerChatbot(answer) {
        if (this.props.message.disableChatbotAnswers) {
            return;
        }
        this.props.message.disableChatbotAnswers = true;
        return this.props.message.thread.post(answer.name, {}, { selected_answer_id: answer.id });
    },
});
