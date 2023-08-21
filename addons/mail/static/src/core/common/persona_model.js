/* @odoo-module */

import { Record, modelRegistry } from "@mail/core/common/record";
import { assignDefined, createLocalId, nullifyClearCommands } from "@mail/utils/common/misc";

/**
 * @typedef {'offline' | 'bot' | 'online' | 'away' | 'im_partner' | undefined} ImStatus
 * @typedef Data
 * @property {number} id
 * @property {string} name
 * @property {string} email
 * @property {'partner'|'guest'} type
 * @property {ImStatus} im_status
 */

export class Persona extends Record {
    static ids = ["id", "type"];
    /** @type {Object.<string, Persona>} */
    static records = {};

    static findById(data) {
        return this.records[this.toId(data)];
    }

    /**
     * @param {import("@mail/core/common/persona_model").Data} data
     * @returns {import("@mail/core/common/persona_model").Persona}
     */
    static insert(data) {
        const localId = this.toId(data);
        let persona = this.records[localId];
        if (!persona) {
            persona = new Persona();
            persona._store = this.store;
            persona.localId = localId;
            this.records[localId] = persona;
        }
        this.update(persona, data);
        // return reactive version
        return this.records[localId];
    }

    static toId(data) {
        return createLocalId(data.type, data.id);
    }

    static update(persona, data) {
        nullifyClearCommands(data);
        assignDefined(persona, { ...data });
        if (
            persona.type === "partner" &&
            persona.im_status !== "im_partner" &&
            !persona.is_public &&
            !this.store.registeredImStatusPartners?.includes(persona.id)
        ) {
            this.store.registeredImStatusPartners?.push(persona.id);
        }
    }

    /** @type {string} */
    localId;
    /** @type {number} */
    id;
    /** @type {'partner' | 'guest'} */
    type;
    /** @type {string} */
    name;
    /** @type {string} */
    displayName;
    /** @type {{ code: string, id: number, name: string}|undefined} */
    country;
    /** @type {string} */
    email;
    /** @type {Array | Object | undefined} */
    user;
    /** @type {ImStatus} */
    im_status;
    isAdmin = false;
    /** @type {import("@mail/core/common/store_service").Store */
    _store;

    get nameOrDisplayName() {
        return this.name || this.displayName;
    }

    get emailWithoutDomain() {
        return this.email.substring(0, this.email.lastIndexOf("@"));
    }
}

modelRegistry.add(Persona.name, Persona);
