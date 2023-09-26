/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

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
    /** @type {Object.<number, import("models").Persona>} */
    static records = {};
    /** @returns {import("models").Persona} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Data} data
     * @returns {import("models").Persona}
     */
    static insert(data) {
        return super.insert(data);
    }

    update(data) {
        assignDefined(this, { ...data });
        if (
            this.type === "partner" &&
            this.im_status !== "im_partner" &&
            !this.is_public &&
            !this._store.registeredImStatusPartners?.includes(this.id)
        ) {
            this._store.registeredImStatusPartners?.push(this.id);
        }
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
