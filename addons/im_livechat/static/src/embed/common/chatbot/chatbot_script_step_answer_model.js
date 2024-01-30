/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class ChatbotScriptStepAnswer extends Record {
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    label;
    /** @type {string|false} */
    redirectLink;
}
ChatbotScriptStepAnswer.register();
