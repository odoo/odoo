/* @odoo-module */

import { assignDefined } from "@mail/utils/common/misc";

/**
 * @typedef IChatbot
 * @property {string} chatbot_name
 * @property {number} chatbot_operator_partner_id
 * @property {number} chatbot_script_id
 * @property {import("@im_livechat/embed/common/chatbot/chatbot_step_model").IChatbotStep[]} chatbot_welcome_steps
 * @property {number} [welcome_step_index]
 */

export class Chatbot {
    /** @type {string} */
    name;
    /** @type {number} */
    partnerId;
    /** @type {number} */
    welcomeStepIndex = 0;
    /** @type {number} */
    scriptId;
    /** @type {import("@im_livechat/embed/common/chatbot/chatbot_step_model").IChatbotStep[]} */
    welcomeSteps = [];

    /**
     * @param {IChatbot} data
     */
    constructor(data) {
        assignDefined(this, data, [
            "name",
            "partnerId",
            "scriptId",
            "welcomeSteps",
            "welcomeStepIndex",
        ]);
    }

    get welcomeCompleted() {
        return this.welcomeStepIndex >= this.welcomeSteps.length;
    }

    get nextWelcomeStep() {
        return this.welcomeSteps[this.welcomeStepIndex++];
    }
}
