/* @odoo-module */

import { assignDefined } from "@mail/utils/common/misc";

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
    operatorFound = false;
    isLast = false;

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

    get expectAnswer() {
        if (
            (this.type === "question_email" && !this.isEmailValid) ||
            (this.answers.length > 0 && !this.hasAnswer)
        ) {
            return true;
        }
        return (
            [
                "free_input_multi",
                "free_input_single",
                "question_selection",
                "question_email",
                "question_phone",
            ].includes(this.type) && !this.hasAnswer
        );
    }
}
