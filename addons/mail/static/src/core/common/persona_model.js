/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";
import { assignDefined, nullifyClearCommands } from "@mail/utils/common/misc";

/**
 * @typedef {'offline' | 'bot' | 'online' | 'away' | 'im_partner' | undefined} ImStatus
 * @typedef Data
 * @property {number} id
 * @property {string} name
 * @property {string} email
 * @property {'partner'|'guest'} type
 * @property {ImStatus} im_status
 */

export class Persona extends DiscussModel {
    static id = ["type", "id"];

    /** @type {string} */
    objectId;
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
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    get nameOrDisplayName() {
        return this.name || this.displayName;
    }

    get emailWithoutDomain() {
        return this.email.substring(0, this.email.lastIndexOf("@"));
    }
}

export class PersonaManager extends DiscussModelManager {
    /** @type {typeof Persona} */
    class;
    /** @type {Object.<number, Persona>} */
    records = {};

    /**
     * @param {import("@mail/core/common/persona_model").Data} data
     * @returns {import("@mail/core/common/persona_model").Persona}
     */
    insert(data) {
        const objectId = this._createObjectId(data);
        let persona = this.records[objectId];
        if (!persona) {
            persona = new Persona();
            persona._store = this.store;
            persona.objectId = objectId;
            this.records[objectId] = persona;
        }
        this.update(persona, data);
        // return reactive version
        return this.records[objectId];
    }

    update(persona, data) {
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
}

discussModelRegistry.add("Persona", [Persona, PersonaManager]);
