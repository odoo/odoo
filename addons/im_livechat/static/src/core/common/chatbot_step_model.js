import { AND, fields, Record } from "@mail/model/export";

export class ChatbotStep extends Record {
    static id = AND("scriptStep", "message");

    setup() {
        super.setup(...arguments);
        this.onChange(
            () => [this.operatorFound],
            function onOperatorFoundChange() {
                if (this.operatorFound) {
                    this.operatorFoundEver = true;
                }
            }
        );
        this.onChange(
            () => [this.selectedAnswer],
            function onSelectedAnswerChange() {
                if (this.selectedAnswer) {
                    this.selectedAnswerEver = this.selectedAnswer;
                }
            }
        );
    }

    /**
     * Pair identifying this step for the python store index.
     *
     * @type {[number, number]|undefined}
     */
    id;
    completed = false;
    /** @type {boolean|undefined} */
    operatorFound;

    /**
     * ChatbotStep isn't a real server model, so `__version__` can't order its writes:
     * a stale `false` can be applied after the real `true`. This field can only move from
     * `false` to `true`, never back, so it stays correct regardless of which one lands last.
     */
    operatorFoundEver = false;
    scriptStep = fields.One("chatbot.script.step");
    message = fields.One("mail.message", { inverse: "chatbotStep" });
    answer_ids = this.computed(() => this.scriptStep?.answer_ids ?? []);
    selectedAnswer = fields.One("chatbot.script.answer");
    /** Same unversioned-model problem, and same one-way fix, as `operatorFoundEver`. */
    selectedAnswerEver = fields.One("chatbot.script.answer");
    step_type = this.computed(() => this.scriptStep?.step_type);
    isLast = false;

    get expectAnswer() {
        return this.scriptStep?.expectAnswer;
    }
}
ChatbotStep.register();
