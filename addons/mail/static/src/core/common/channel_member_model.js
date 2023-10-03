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
    /**
     * @param {Object|Array} data
     * @returns {import("models").ChannelMember}
     */
    static insert(data) {
        /** @type {import("models").ChannelMember} */
        const member = this.preinsert(data);
        member.update(data);
        return member;
    }

    update(data) {
        this.id = data.id;
        if ("persona" in data) {
            this.persona = {
                ...(data.persona.partner ?? data.persona.guest),
                type: data.persona.guest ? "guest" : "partner",
                country: data.persona.partner?.country,
                channelId: data.persona.guest ? data.channel.id : null,
            };
        }
        let thread = data.thread ?? this.thread;
        if (!thread && data.channel?.id) {
            thread = {
                id: data.channel.id,
                model: "discuss.channel",
            };
        }
        this.thread ??= thread;
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
