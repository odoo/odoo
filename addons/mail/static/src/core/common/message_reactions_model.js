/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";

export class MessageReactions extends Record {
    static id = AND("message", "content");
    /** @returns {import("models").Models["MessageReactions"]} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {import("models").Models["MessageReactions"]} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {import("models").Models["MessageReactions"]}
     */
    static insert(data) {
        let reaction = this.store.Message.get(data.message.id)?.reactions.find(
            ({ content }) => content === data.content
        );
        if (!reaction) {
            reaction = this.new(data);
        }
        const personasToUnlink = new Set();
        const alreadyKnownPersonaIds = new Set(reaction.personas.map((p) => p.localId));
        for (const rawPartner of data.partners) {
            const [command, partnerData] = Array.isArray(rawPartner)
                ? rawPartner
                : ["insert", rawPartner];
            const persona = this.store.Persona.insert({ ...partnerData, type: "partner" });
            if (command === "insert" && !alreadyKnownPersonaIds.has(persona.localId)) {
                reaction.personas.push(persona);
            } else if (command !== "insert") {
                personasToUnlink.add(persona.localId);
            }
        }
        for (const rawGuest of data.guests) {
            const [command, guestData] = Array.isArray(rawGuest) ? rawGuest : ["insert", rawGuest];
            const persona = this.store.Persona.insert({ ...guestData, type: "guest" });
            if (command === "insert" && !alreadyKnownPersonaIds.has(persona.localId)) {
                reaction.personas.push(persona);
            } else if (command !== "insert") {
                personasToUnlink.add(persona.localId);
            }
        }
        Object.assign(reaction, {
            count: data.count,
            content: data.content,
            message: this.store.Message.insert(data.message),
            personas: reaction.personas.filter((p) => !personasToUnlink.has(p)),
        });
        return reaction;
    }

    /** @type {string} */
    content;
    /** @type {number} */
    count;
    personas = Record.List("Persona");
    message = Record.one("Message");
}

MessageReactions.register();
