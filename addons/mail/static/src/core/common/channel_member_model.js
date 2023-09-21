/* @odoo-module */

import { Record } from "@mail/core/common/record";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {import("models").Persona} persona
 * @property {import("models").Thread} thread
 */
export class ChannelMember extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Models["ChannelMember"]>} */
    static records = {};
    /** @returns {import("models").Models["ChannelMember"]} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {import("models").Models["ChannelMember"]} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object|Array} data
     * @returns {import("models").Models["ChannelMember"]}
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
