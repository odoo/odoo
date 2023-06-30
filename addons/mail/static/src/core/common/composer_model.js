/* @odoo-module */

export class Composer {
    /** @type {import("@mail/core/common/attachment_model").Attachment[]} */
    attachments = [];
    /** @type {import("@mail/core/common/message_model").Message} */
    message;
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
    /** @typedef {'message' | 'note' | false} */
    type;
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
            type: thread?.type === "chatter" ? false : "message",
            _store: store,
        });
    }
}
