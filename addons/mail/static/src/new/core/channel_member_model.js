/* @odoo-module */

import { createLocalId } from "../utils/misc";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {string} personaLocalId
 * @property {number} threadId
 */
export class ChannelMember {
    personaLocalId;
    threadId;
    typingTimer;
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;

    get persona() {
        return this._store.personas[this.personaLocalId];
    }

    set persona(persona) {
        this.personaLocalId = persona?.localId;
    }

    get thread() {
        return this._store.threads[createLocalId("mail.channel", this.threadId)];
    }
}
