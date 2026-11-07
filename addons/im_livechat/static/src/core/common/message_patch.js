import { Message } from "@mail/core/common/message";

import { useProps, t } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(Message.prototype, {
    setup() {
        super.setup();
        this.livechatProps = useProps({ isTypingMessage: t.boolean().optional() });
        this.url = url;
    },

    get showChatbotAnswers() {
        const chatbotStep = this.props.message.chatbotStep;
        const channel = this.props.message.channel_id;
        return (
            chatbotStep?.answer_ids.length > 0 &&
            channel?.selfMemberType === "visitor" &&
            !(chatbotStep.selectedAnswerEver || channel.chatbot?.completed)
        );
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
