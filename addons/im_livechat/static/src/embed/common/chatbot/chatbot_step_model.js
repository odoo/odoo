import { AND, Record } from "@mail/core/common/record";

export class ChatbotStep extends Record {
    static id = AND("scriptStep", "message");

    operatorFound = Record.attr(false, {
        /**
         * Cannot change from having found an operator to not having found one.
         *
         * @this {import("models").ChatbotStep}
         */
        ignoreUpdateWhen(new_val) {
            return this.operatorFound && !new_val;
        },
    });
    scriptStep = Record.one("chatbot.script.step");
    message = Record.one("mail.message", { inverse: "chatbotStep" });
    answers = Record.many("chatbot.script.answer", {
        compute() {
            return this.scriptStep?.answers;
        },
    });
    selectedAnswer = Record.one("chatbot.script.answer");
    type = Record.attr("", {
        compute() {
            return this.scriptStep?.type;
        },
    });
    isLast = false;

    get expectAnswer() {
        return [
            "free_input_multi",
            "free_input_single",
            "question_selection",
            "question_email",
            "question_phone",
        ].includes(this.type);
    }
}
ChatbotStep.register();
