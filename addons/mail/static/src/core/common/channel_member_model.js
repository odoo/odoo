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
    /** @type {Object.<number, import("models").ChannelMember>} */
    static records = {};
    /** @returns {import("models").ChannelMember} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ChannelMember|import("models").ChannelMember[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {number} */
    id;
    persona = Record.one("Persona", { inverse: "channelMembers" });
    rtcSession = Record.one("RtcSession");
    thread = Record.one("Thread", { inverse: "channelMembers" });

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }
}

ChannelMember.register();
