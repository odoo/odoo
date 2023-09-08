/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";

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
    static id = AND("type", "id");
    /** @type {Object.<number, Persona>} */
    static records = {};
    /** @returns {Persona} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {Persona} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Data} data
     * @returns {Persona}
     */
    static insert(data) {
        const persona = this.get(data) ?? this.new(data);
        this.env.services["mail.persona"].update(persona, data);
        // return reactive version
        return persona;
    }

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

    get nameOrDisplayName() {
        return this.name || this.displayName;
    }

    get emailWithoutDomain() {
        return this.email.substring(0, this.email.lastIndexOf("@"));
    }
}

Persona.register();
