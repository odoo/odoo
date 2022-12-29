/* @odoo-module */

export class Composer {
    /** @type {Message} */
    message;
    /** @type {string} */
    textInputContent;
    /** @type {Thread} */
    thread;
    /** @type {{ start: number, end: number, direction: "forward" | "backward" | "none"}}*/
    selection = {
        start: 0,
        end: 0,
        direction: "none",
    };
    /** @type {Boolean} */
    forceCursorMove;
    /** @typedef {'message' | 'note'| false} */
    type;
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;

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
