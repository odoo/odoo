/* @odoo-module */

import { DiscussModel } from "@mail/core/common/discuss_model";

export class MessageReactions extends DiscussModel {
    /** @type {string} */
    content;
    /** @type {number} */
    count;
    /** @type {number[]} */
    personaObjectIds = [];
    /** @type {number} */
    messageId;
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    /** @type {import("@mail/core/common/persona_model").Persona[]} */
    get personas() {
        return this.personaObjectIds.map((objectId) => this._store.Persona[objectId]);
    }
}
