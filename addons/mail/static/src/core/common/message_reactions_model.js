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
    nextId = 0;
    /** @type {typeof MessageReactions} */
    class;
    /** @type {Object.<number, MessageReactions>} */
    records = {};

    /**
     * @param {Object} data
     * @returns {MessageReactions}
     */
    insert(data) {
        let reaction = this.store.Message.records[data.message.id]?.reactions.find(
            ({ content }) => content === data.content
        );
        if (!reaction) {
            reaction = new MessageReactions();
            reaction._store = this.store;
            reaction.objectId = this._createObjectId(data);
        }
        const personasToUnlink = new Set();
        const alreadyKnownPersonaIds = new Set(reaction.personaObjectIds);
        for (const rawPartner of data.partners) {
            const [command, partnerData] = Array.isArray(rawPartner)
                ? rawPartner
                : ["insert", rawPartner];
            const persona = this.store.Persona.insert({ ...partnerData, type: "partner" });
            if (command === "insert" && !alreadyKnownPersonaIds.has(persona.objectId)) {
                reaction.personaObjectIds.push(persona.objectId);
            } else if (command !== "insert") {
                personasToUnlink.add(persona.objectId);
            }
        }
        for (const rawGuest of data.guests) {
            const [command, guestData] = Array.isArray(rawGuest) ? rawGuest : ["insert", rawGuest];
            const persona = this.store.Persona.insert({ ...guestData, type: "guest" });
            if (command === "insert" && !alreadyKnownPersonaIds.has(persona.objectId)) {
                reaction.personaObjectIds.push(persona.objectId);
            } else if (command !== "insert") {
                personasToUnlink.add(persona.objectId);
            }
        }
        Object.assign(reaction, {
            count: data.count,
            content: data.content,
            messageId: data.message.id,
            personaObjectIds: reaction.personaObjectIds.filter(
                (objectId) => !personasToUnlink.has(objectId)
            ),
        });
        return reaction;
    }
}

discussModelRegistry.add("MessageReactions", [MessageReactions, MessageReactionsManager]);
