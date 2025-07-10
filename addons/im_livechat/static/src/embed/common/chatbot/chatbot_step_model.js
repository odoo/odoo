import { AND, Record } from "@mail/core/common/record";

export class ChatbotStep extends Record {
    static id = AND("scriptStep", "message");

<<<<<<< 178dff30131a93680dfd994fd22b29a766ee9354
||||||| 5ea09d68a8ac8cf2b8bb62330875728772849d49
/**
 * @typedef StepAnswer
 * @property {number} id
 * @property {string} label
 * @property {string} [redirectLink]
 */

/**
 * @typedef { "free_input_multi"|"free_input_single"|"question_email"|"question_phone"|"question_selection"|"text"|"forward_operator"} StepType
 */

/**
 * @typedef IChatbotStep
 * @property {number} id
 * @property {boolean} isLast
 * @property {string} message
 * @property {StepType} type
 * @property {StepAnswer[]} [answers]
 * @property {boolean} [operatorFound]
 * @property {boolean} [isEmailValid]
 * @property {number} [selectedAnswerId]
 * @property {boolean} [hasAnswer]
 */

export class ChatbotStep {
    /** @type {number} */
    id;
    /** @type {StepAnswer[]} */
    answers = [];
    /** @type {string} */
    message;
    /** @type {StepType} */
    type;
    hasAnswer = false;
    isEmailValid = false;
=======
/**
 * @typedef StepAnswer
 * @property {number} id
 * @property {string} label
 * @property {string} [redirectLink]
 */

/**
 * @typedef { "free_input_multi"|"free_input_single"|"question_email"|"question_phone"|"question_selection"|"text"|"forward_operator"} StepType
 */

/**
 * @typedef IChatbotStep
 * @property {number} id
 * @property {boolean} isLast
 * @property {string} message
 * @property {StepType} type
 * @property {StepAnswer[]} [answers]
 * @property {boolean} [operatorFound]
 * @property {boolean} [isEmailValid]
 * @property {number} [selectedAnswerId]
 * @property {boolean} [hasAnswer]
 */

export class ChatbotStep {
    /** @type {number} */
    id;
    /** @type {number} */
    sequence;
    /** @type {StepAnswer[]} */
    answers = [];
    /** @type {string} */
    message;
    /** @type {StepType} */
    type;
    hasAnswer = false;
    isEmailValid = false;
>>>>>>> cb50eda9cb2391054f77c222fd0b6a38365ee0bc
    operatorFound = false;
    scriptStep = Record.one("chatbot.script.step");
    message = Record.one("Message", { inverse: "chatbotStep" });
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

<<<<<<< 178dff30131a93680dfd994fd22b29a766ee9354
||||||| 5ea09d68a8ac8cf2b8bb62330875728772849d49
    /**
     * @param {IChatbotStep} data
     */
    constructor(data) {
        assignDefined(this, data, [
            "answers",
            "id",
            "isLast",
            "message",
            "operatorFound",
            "hasAnswer",
            "type",
            "isEmailValid",
        ]);
        this.hasAnswer = data.hasAnswer ?? Boolean(data.selectedAnswerId);
    }

=======
    /**
     * @param {IChatbotStep} data
     */
    constructor(data) {
        assignDefined(this, data, [
            "answers",
            "id",
            "isLast",
            "message",
            "operatorFound",
            "hasAnswer",
            "type",
            "isEmailValid",
            "sequence",
        ]);
        this.hasAnswer = data.hasAnswer ?? Boolean(data.selectedAnswerId);
    }

>>>>>>> cb50eda9cb2391054f77c222fd0b6a38365ee0bc
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
