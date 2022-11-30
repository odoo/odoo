/** @odoo-module **/

import { convertBrToLineBreak } from "@mail/new/utils";

export class Composer {
    static insert(state, data) {
        const composer = new Composer(data);
        if (data.messageId) {
            composer.textInputContent = convertBrToLineBreak(state.messages[data.messageId].body);
        }
        return composer;
    }

    constructor({ threadId, messageId }) {
        Object.assign(this, {
            messageId,
            threadId,
            textInputContent: "",
        });
    }
}
