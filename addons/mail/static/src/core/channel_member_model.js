/* @odoo-module */

import { deserializeDateTime } from "@web/core/l10n/dates";
import { createLocalId } from "../utils/misc";
import { Record } from "@mail/core/record";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {string} personaLocalId
 * @property {number} threadId
 */
export class ChannelMember extends Record {
    /** @type {number} */
    id;
    personaLocalId;
    rtcSessionId;
    create_date;
    threadId;
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
        return this._store.threads[createLocalId("discuss.channel", this.threadId)];
    }

    get memberSince() {
        return deserializeDateTime(this.create_date);
    }
}
