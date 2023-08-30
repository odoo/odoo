/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { createLocalId } from "@mail/utils/common/misc";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {string} personaLocalId
 * @property {number} threadId
 */
export class ChannelMember extends Record {
    /** @type {Object.<number, ChannelMember>} */
    static records = {};
    /**
     * @param {Object|Array} data
     * @returns {ChannelMember}
     */
    static insert(data) {
        const memberData = Array.isArray(data) ? data[1] : data;
        let member = this.records[memberData.id];
        if (!member) {
            this.records[memberData.id] = new ChannelMember();
            member = this.records[memberData.id];
            member._store = this.store;
        }
        this.env.services["discuss.channel.member"].update(member, data);
        return member;
    }

    /** @type {number} */
    id;
    personaLocalId;
    rtcSessionId;
    threadId;
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    get persona() {
        return this._store.Persona.records[this.personaLocalId];
    }

    set persona(persona) {
        this.personaLocalId = persona?.localId;
    }

    get rtcSession() {
        return this._store.RtcSession.records[this.rtcSessionId];
    }

    get thread() {
        return this._store.Thread.records[createLocalId("discuss.channel", this.threadId)];
    }

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }
}

ChannelMember.register();
