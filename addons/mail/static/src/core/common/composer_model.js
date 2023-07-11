/* @odoo-module */

/**
 * @typedef {{partnerIds: Set<number>, threadIds: Set<number>}} RawMentions
 */

export class Composer {
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

    constructor(store, data) {
        const { message, thread } = data;
        if (thread) {
            this.thread = thread;
            thread.composer = this;
        } else if (message) {
            this.message = message;
            message.composer = this;
        }
        Object.assign(this, {
            textInputContent: "",
            _store: store,
        });
    }
}
