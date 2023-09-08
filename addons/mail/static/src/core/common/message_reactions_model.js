/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";

export class MessageReactions extends Record {
    static id = AND("message", "content");
    /** @returns {MessageReactions} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {MessageReactions} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {MessageReactions}
     */
    static insert(data) {
        let reaction = this.store.Message.get(data.message.id)?.reactions.find(
            ({ content }) => content === data.content
        );
        if (!reaction) {
            reaction = this.new(data);
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
    message = Record.one("Message");

    /** @type {import("@mail/core/common/persona_model").Persona[]} */
    get personas() {
        return this.personaLocalIds.map((localId) => this._store.Persona.records[localId]);
    }
}

MessageReactions.register();
