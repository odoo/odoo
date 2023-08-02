/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";

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
        return this.personaObjectIds.map((objectId) => this._store.Persona.records[objectId]);
    }
}

export class MessageReactionsManager extends DiscussModelManager {
    /** @type {typeof MessageReactions} */
    class;
    /** @type {Object.<number, MessageReactions>} */
    records = {};
}

discussModelRegistry.add("MessageReactions", [MessageReactions, MessageReactionsManager]);
