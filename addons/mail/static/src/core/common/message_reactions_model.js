/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class MessageReactions extends Record {
    static id = Record.AND("content", "message");
    /**
     * @param {Object} data
     * @returns {MessageReactions}
     */
    static insert(data) {
        let reaction = this.store.Message.get(data.message)?.reactions.find(
            ({ content }) => content === data.content
        );
        if (!reaction) {
            reaction = this.new(data);
            reaction._store = this.store;
        }
        const personasToUnlink = new Set();
        const alreadyKnownPersonaIds = new Set(reaction.personaLocalIds);
        for (const rawPartner of data.partners) {
            const [command, partnerData] = Array.isArray(rawPartner)
                ? rawPartner
                : ["insert", rawPartner];
            const persona = this.store.Persona.insert({ ...partnerData, type: "partner" });
            if (command === "insert" && !alreadyKnownPersonaIds.has(persona.localId)) {
                reaction.personaLocalIds.push(persona.localId);
            } else if (command !== "insert") {
                personasToUnlink.add(persona.localId);
            }
        }
        for (const rawGuest of data.guests) {
            const [command, guestData] = Array.isArray(rawGuest) ? rawGuest : ["insert", rawGuest];
            const persona = this.store.Persona.insert({ ...guestData, type: "guest" });
            if (command === "insert" && !alreadyKnownPersonaIds.has(persona.localId)) {
                reaction.personaLocalIds.push(persona.localId);
            } else if (command !== "insert") {
                personasToUnlink.add(persona.localId);
            }
        }
        Object.assign(reaction, {
            count: data.count,
            content: data.content,
            message: data.message,
            personaLocalIds: reaction.personaLocalIds.filter(
                (localId) => !personasToUnlink.has(localId)
            ),
        });
        return reaction;
    }

    /** @type {string} */
    content;
    /** @type {number} */
    count;
    /** @type {number[]} */
    personaLocalIds = [];
    /** @type {import("@mail/core/common/message_model").Message[]} */
    message = Record.one();
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    /** @type {import("@mail/core/common/persona_model").Persona[]} */
    get personas() {
        return this.personaLocalIds.map((localId) => this._store.Persona.records[localId]);
    }
}

MessageReactions.register();
