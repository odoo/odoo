/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class ThreadSeenInfo extends Record {
    static id = "id";
    /** @type {Object.<string, import("models").ThreadSeenInfo>} */
    static records = {};
    /** @returns {import("models").ThreadSeenInfo} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ThreadSeenInfo|import("models").ThreadSeenInfo[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    /** @typedef {number} */
    id;
    lastFetchedMessage = Record.one("Message");
    lastSeenMessage = Record.one("Message");
    partner = Record.one("Persona");
}

ThreadSeenInfo.register();
