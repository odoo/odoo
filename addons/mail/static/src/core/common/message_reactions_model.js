/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";

export class MessageReactions extends Record {
    static id = AND("message", "content");
    /** @returns {import("models").MessageReactions} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {import("models").MessageReactions}
     */
    static insert(data) {
        if (data.message && !(data.message instanceof Record)) {
            data.message = this.store.Message.insert(data.message);
        }
        let reaction = data.message.reactions.find(({ content }) => content === data.content);
        if (!reaction) {
            /** @type {import("models").MessageReactions} */
            reaction = this.preinsert(data);
        }
        Object.assign(reaction, data);
        return reaction;
    }

    /** @type {string} */
    content;
    /** @type {number} */
    count;
    personas = Record.many("Persona");
    message = Record.one("Message");
}

MessageReactions.register();
