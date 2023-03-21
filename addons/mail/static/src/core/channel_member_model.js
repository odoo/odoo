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
    rtcSessionId;
    threadId;
    typingTimer;
    /** @type {import("@mail/core/store_service").Store} */
    _store;

    get persona() {
        return this._store.personas[this.personaLocalId];
    }

    set persona(persona) {
        this.personaLocalId = persona?.localId;
    }

    get rtcSession() {
        return this._store.rtcSessions[this.rtcSessionId];
    }

    get thread() {
        return this._store.threads[createLocalId("mail.channel", this.threadId)];
    }
}
