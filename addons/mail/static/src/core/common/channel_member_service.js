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
    }

    /**
     * @param {import("models").ChannelMember} member
     * @returns {string}
     */
    getName(member) {
        return member.persona.nameOrDisplayName;
    }
}

export const channelMemberService = {
    dependencies: ["mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new ChannelMemberService(env, services);
    },
};
registry.category("services").add("discuss.channel.member", channelMemberService);
