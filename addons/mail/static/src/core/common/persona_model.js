/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { createLocalId } from "@mail/utils/common/misc";

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
    /** @type {Object.<number, Persona>} */
    static records = {};
    /**
     * @param {Data} data
     * @returns {Persona}
     */
    static insert(data) {
        const localId = createLocalId(data.type, data.id);
        let persona = this.records[localId];
        if (!persona) {
            persona = new Persona();
            persona._store = this.store;
            persona.localId = localId;
            this.records[localId] = persona;
        }
        this.env.services["mail.persona"].update(persona, data);
        // return reactive version
        return this.records[localId];
    }

    /** @type {string} */
    localId;
    /** @type {number} */
    id;
    /** @type {boolean | undefined} */
    is_company;
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
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    get nameOrDisplayName() {
        return this.name || this.displayName;
    }

    get emailWithoutDomain() {
        return this.email.substring(0, this.email.lastIndexOf("@"));
    }
}

Persona.register();
