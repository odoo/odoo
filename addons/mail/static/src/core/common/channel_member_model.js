/* @odoo-module */

import { createObjectId } from "@mail/utils/common/misc";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {string} personaObjectId
 * @property {number} threadId
 */
export class ChannelMember {
    /** @type {number} */
    id;
    personaObjectId;
    rtcSessionId;
    threadId;
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    get persona() {
        return this._store.personas[this.personaObjectId];
    }

    set persona(persona) {
        this.personaObjectId = persona?.objectId;
    }

    get rtcSession() {
        return this._store.rtcSessions[this.rtcSessionId];
    }

    get thread() {
        return this._store.threads[createObjectId("Thread", "discuss.channel", this.threadId)];
    }

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }
}
