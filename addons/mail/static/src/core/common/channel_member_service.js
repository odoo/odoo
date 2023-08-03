/* @odoo-module */

import { registry } from "@web/core/registry";

export class ChannelMemberService {
    constructor(env, { "mail.store": store }) {
        this.env = env;
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = store;
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
    start(env, services) {
        return new ChannelMemberService(env, services);
    },
};
registry.category("services").add("discuss.channel.member", channelMemberService);
