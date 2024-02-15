import { AND, Record } from "@mail/core/common/record";

export class ChatbotStep extends Record {
    static id = AND("scriptStep", "message");

    operatorFound = false;
    scriptStep = Record.one("ChatbotScriptStep");
    message = Record.one("Message", { inverse: "chatbotStep" });
    answers = Record.many("ChatbotScriptStepAnswer", {
        compute() {
            return this.scriptStep?.answers;
        },
    });
    selectedAnswer = Record.one("ChatbotScriptStepAnswer");
    type = Record.attr("", {
        compute() {
            return this.scriptStep?.type;
        },
    });
    isLast = Record.attr(false, {
        compute() {
            return this.scriptStep.isLast;
        },
    });

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
