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
    personaLocalId;
    rtcSessionId;
    threadId;

    get persona() {
        return this._store.Persona.records[this.personaLocalId];
    }

    set persona(persona) {
        this.personaLocalId = persona?.localId;
    }

    get rtcSession() {
        return this._store.RtcSession.get(this.rtcSessionId);
    }

    get thread() {
        return this._store.Thread.get({ model: "discuss.channel", id: this.threadId });
    }

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }
}

ChannelMember.register();
