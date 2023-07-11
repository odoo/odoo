/* @odoo-module */

export class Composer {
    /** @type {import("@mail/attachments/attachment_model").Attachment[]} */
    attachments = [];
    /** @type {import("@mail/core/message_model").Message} */
    message;
    rawMentions = {
        partnerIds: new Set(),
        threadIds: new Set(),
    };
    /** @type {string} */
    textInputContent;
    /** @type {import("@mail/core/thread_model").Thread */
    thread;
    /** @type {{ start: number, end: number, direction: "forward" | "backward" | "none"}}*/
    selection = {
        start: 0,
        end: 0,
        direction: "none",
    };
    /** @type {boolean} */
    forceCursorMove;
    /** @type {import("@mail/core/store_service").Store} */
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
