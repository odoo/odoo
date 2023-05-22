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
    wysiwygValue = undefined;
    /** @type {import("@mail/core/thread_model").Thread */
    thread;
    /** @type {Range} */
    range = undefined;
    /** @typedef {'message' | 'note' | false} */
    type;
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
            wysiwygValue: "<p><br/></p>",
            textContent: "",
            type: thread?.type === "chatter" ? false : "message",
            _store: store,
        });
    }
}
