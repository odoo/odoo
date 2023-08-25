/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class MessageReactions extends Record {
    /** @type {string} */
    content;
    /** @type {number} */
    count;
    /** @type {number[]} */
    personaLocalIds = [];
    /** @type {number} */
    messageId;
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    /** @type {import("@mail/core/common/persona_model").Persona[]} */
    get personas() {
        return this.personaLocalIds.map((localId) => this._store.Persona.records[localId]);
    }
}
