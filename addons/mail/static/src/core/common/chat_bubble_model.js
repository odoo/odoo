/* @odoo-module */

import { Record } from "@mail/core/common/record";

/** @typedef {{ thread?: import("models").Thread }} ChatBubbleData */

export class ChatBubble extends Record {
    static id = "thread";
    /** @type {Object<number, import("models").ChatBubble} */
    static records = {};
    /** @returns {import("models").ChatBubble} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ChatBubble|import("models").ChatBubble[]} */
    static insert() {
        return super.insert(...arguments);
    }
    /**
     * @param {ChatBubbleData} [data]
     * @returns {import("models").ChatBubble}
     */
    static _insert(data = {}) {
        const chatBubble = super._insert(...arguments);
        if (!this.store.discuss.chatBubbles.includes(chatBubble)) {
            this.store.discuss.chatBubbles.add(chatBubble);
        }
        return chatBubble;
    }

    thread = Record.one("Thread");
}

ChatBubble.register();
