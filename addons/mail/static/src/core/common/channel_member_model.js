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
        const member = this.get(memberData) ?? this.new(memberData);
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

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }
}

ChannelMember.register();
