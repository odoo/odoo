/* @odoo-module */

import { OR, Record } from "@mail/core/common/record";

/**
 * @typedef {{partnerIds: Set<number>, threadIds: Set<number>}} RawMentions
 */

export class Composer extends Record {
    static id = OR("thread", "message");
    /** @returns {Composer} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {Composer} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {Composer}
     */
    static insert(data) {
        const { message, thread } = data;
        if (Boolean(message) === Boolean(thread)) {
            throw new Error("Composer shall have a thread xor a message.");
        }
        let composer = (thread ?? message)?.composer;
        if (!composer) {
            composer = this.new(data);
            const { message, thread } = data;
            if (thread) {
                composer.thread = thread;
                Object.assign(composer, { thread });
                Object.assign(thread, { composer });
            } else if (message) {
                Object.assign(composer, { message });
                Object.assign(message, { composer });
            }
            Object.assign(composer, { textInputContent: "" });
        }
        if ("textInputContent" in data) {
            composer.textInputContent = data.textInputContent;
        }
        if ("selection" in data) {
            Object.assign(composer.selection, data.selection);
        }
        if ("mentions" in data) {
            for (const mention of data.mentions) {
                if (mention.type === "partner") {
                    composer.rawMentions.partnerIds.add(mention.id);
                }
            }
        }
        return composer;
    }

    attachments = Record.List("Attachment");
    message = Record.one("Message");
    /** @type {RawMentions} */
    rawMentions = {
        partnerIds: new Set(),
        threadIds: new Set(),
    };
    cannedResponses = Record.Set("CannedResponse");
    /** @type {string} */
    textInputContent;
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
