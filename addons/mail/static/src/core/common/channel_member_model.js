/* @odoo-module */

import { Record } from "@mail/core/common/record";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {string} personaLocalId
 * @property {number} threadId
 */
export class ChannelMember extends Record {
    static id = "id";
    /** @type {Object.<number, ChannelMember>} */
    static records = {};
    /**
     * @param {Object|Array} data
     * @returns {ChannelMember}
     */
    static insert(data) {
        const memberData = Array.isArray(data) ? data[1] : data;
        let member = this.get(memberData);
        if (!member) {
            member = this.new(memberData);
            this.records[member.localId] = member;
            member = this.records[member.localId];
            member._store = this.store;
        }
        this.env.services["discuss.channel.member"].update(member, data);
        return member;
    }

    /** @type {number} */
    id;
    /** @type {import("@mail/core/common/persona_model").Persona} */
    persona = Record.one();
    /** @type {import("@mail/discuss/call/common/rtc_session_model").RtcSession} */
    rtcSession = Record.one();
    /** @type {import("@mail/core/common/thread_model").Thread} */
    thread = Record.one();
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }
}

ChannelMember.register();
