/* @odoo-module */

import { OR, Record } from "@mail/core/common/record";

export class Composer extends Record {
    static id = OR("thread", "message");
    /** @returns {import("models").Composer} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {import("models").Composer}
     */
    static insert(data) {
        const { message, thread } = data;
        if (Boolean(message) === Boolean(thread)) {
            throw new Error("Composer shall have a thread xor a message.");
        }
        /** @type {import("models").Composer} */
        const composer = this.preinsert(data);
        if ("textInputContent" in data) {
            composer.textInputContent = data.textInputContent;
        }
        if ("selection" in data) {
            composer.selection = data.selection;
        }
        if ("mentionedPartners" in data) {
            composer.mentionedPartners = data.mentionedPartners;
        }
        return composer;
    }

    attachments = Record.many("Attachment");
    message = Record.one("Message");
    mentionedPartners = Record.many("Persona");
    mentionedChannels = Record.many("Thread");
    cannedResponses = Record.many("CannedResponse");
    textInputContent = "";
    thread = Record.one("Thread");
    /** @type {{ start: number, end: number, direction: "forward" | "backward" | "none"}}*/
    selection = {
        start: 0,
        end: 0,
        direction: "none",
    };
    /** @type {boolean} */
    forceCursorMove;
    isFocused = false;
}

Composer.register();
