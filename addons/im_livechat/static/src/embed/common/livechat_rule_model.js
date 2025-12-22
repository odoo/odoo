import { Record } from "@mail/core/common/record";

export class LivechatRule extends Record {
    /** @type {"auto_popup"|"display_button_and_text"|undefined} */
    action;
    /** @type {number} */
    autoPopupTimer;
    /** @type {string} */
    regexURL;
    chatbotScript = Record.one("ChatbotScript");
}
LivechatRule.register();
