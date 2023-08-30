/* @odoo-module */

import { Record } from "@mail/core/common/record";

/**
 * @typedef {{partnerIds: Set<number>, threadIds: Set<number>}} RawMentions
 */

export class Composer extends Record {
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
            composer = new Composer();
            const { message, thread } = data;
            if (thread) {
                composer.thread = thread;
                Object.assign(composer, { thread });
                Object.assign(thread, { composer });
            } else if (message) {
                Object.assign(composer, { message });
                Object.assign(message, { composer });
            }
            Object.assign(composer, {
                textInputContent: "",
                _store: this.store,
            });
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

    /** @type {import("@mail/core/common/attachment_model").Attachment[]} */
    attachments = [];
    /** @type {import("@mail/core/common/message_model").Message} */
    message;
    /** @type {RawMentions} */
    rawMentions = {
        partnerIds: new Set(),
        threadIds: new Set(),
    };
    /** @type {Set<number>} */
    cannedResponseIds = new Set();
    /** @type {string} */
    textInputContent;
    /** @type {import("@mail/core/common/thread_model").Thread */
    thread;
    /** @type {{ start: number, end: number, direction: "forward" | "backward" | "none"}}*/
    selection = {
        start: 0,
        end: 0,
        direction: "none",
    };
    /** @type {boolean} */
    forceCursorMove;
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;
    isFocused = false;
}

Composer.register();
