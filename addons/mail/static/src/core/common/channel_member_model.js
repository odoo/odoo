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
    static new(data) {
        return super.new(data);
    }
    /** @returns {import("models").ChannelMember} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object|Array} data
     * @returns {import("models").ChannelMember}
     */
    static insert(data) {
        const memberData = Array.isArray(data) ? data[1] : data;
        const member = this.get(memberData) ?? this.new(memberData);
        member.update(data);
        return member;
    }

    update(data) {
        const [command, memberData] = Array.isArray(data) ? data : ["ADD", data];
        this.id = memberData.id;
        if ("persona" in memberData) {
            this.persona = this._store.Persona.insert({
                ...(memberData.persona.partner ?? memberData.persona.guest),
                type: memberData.persona.guest ? "guest" : "partner",
                country: memberData.persona.partner?.country,
                channelId: memberData.persona.guest ? memberData.channel.id : null,
            });
        }
        let thread = memberData.thread ?? this.thread;
        if (!thread && memberData.channel?.id) {
            thread = this._store.Thread.insert({
                id: memberData.channel.id,
                model: "discuss.channel",
            });
        }
        if (thread && !this.thread) {
            this.thread = thread;
        }
        switch (command) {
            case "ADD":
                this.thread?.channelMembers.add(this);
                break;
            case "DELETE":
                this.delete();
                break;
        }
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
