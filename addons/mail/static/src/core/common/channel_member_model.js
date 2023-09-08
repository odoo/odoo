/* @odoo-module */

import { Record } from "@mail/core/common/record";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {import("@mail/core/common/persona_model").Persona} persona
 * @property {import("@mail/core/common/thread_model").Thread} thread
 */
export class ChannelMember extends Record {
    static id = "id";
    /** @type {Object.<number, ChannelMember>} */
    static records = {};
    /** @returns {ChannelMember} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {ChannelMember} */
    static get(data) {
        return super.get(data);
    }
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
    persona = Record.one("Persona");
    rtcSession = Record.one("RtcSession");
    thread = Record.one("Thread");

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }
}

ChannelMember.register();
