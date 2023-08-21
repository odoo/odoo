/* @odoo-module */

import { registry } from "@web/core/registry";

export class ChannelMemberService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.personaService = services["mail.persona"];
    }

    /**
     * @param {Object|Array} data
     * @returns {ChannelMember}
     */
    insert(data) {
        return this.store.ChannelMember.insert(data);
    }

    update(member, data) {
        return this.store.ChannelMember.update(data);
    }

    /**
     * @param {import("@mail/core/common/channel_member_model").ChannelMember} member
     * @returns {string}
     */
    getName(member) {
        return member.persona.nameOrDisplayName;
    }
}

export const channelMemberService = {
    dependencies: ["mail.store", "mail.persona"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new ChannelMemberService(env, services);
    },
};
registry.category("services").add("discuss.channel.member", channelMemberService);
