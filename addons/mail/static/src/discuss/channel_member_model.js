/* @odoo-module */

import { createLocalId } from "@mail/utils/misc";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {string} personaLocalId
 * @property {number} channelId
 */
export class ChannelMember {
    /** @type {number} */
    id;
    personaLocalId;
    rtcSessionId;
    channelId;
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

    get channel() {
        return this._store.channels[createLocalId("discuss.channel", this.channelId)];
    }
}
