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
        let reaction = this.store.Message.get(data.message.id)?.reactions.find(
            ({ content }) => content === data.content
        );
        if (!reaction) {
            /** @type {import("models").MessageReactions} */
            reaction = this.preinsert(data);
        }
        const personasToUnlink = new Set();
        const alreadyKnownPersonaIds = new Set(reaction.personas.map((p) => p.localId));
        for (const rawPartner of data.partners) {
            const [command, partnerData] = Array.isArray(rawPartner)
                ? rawPartner
                : ["ADD", rawPartner];
            const persona = this.store.Persona.insert({ ...partnerData, type: "partner" });
            if (command === "ADD" && !alreadyKnownPersonaIds.has(persona.localId)) {
                reaction.personas.push(persona);
            } else if (command !== "ADD") {
                personasToUnlink.add(persona.localId);
            }
        }
        for (const rawGuest of data.guests) {
            const [command, guestData] = Array.isArray(rawGuest) ? rawGuest : ["ADD", rawGuest];
            const persona = this.store.Persona.insert({ ...guestData, type: "guest" });
            if (command === "ADD" && !alreadyKnownPersonaIds.has(persona.localId)) {
                reaction.personas.push(persona);
            } else if (command !== "ADD") {
                personasToUnlink.add(persona.localId);
            }
        }
        Object.assign(reaction, {
            count: data.count,
            content: data.content,
            message: data.message,
            personas: reaction.personas.filter((p) => !personasToUnlink.has(p)),
        });
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
