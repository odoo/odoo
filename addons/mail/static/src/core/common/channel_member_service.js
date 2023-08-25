/* @odoo-module */

import { ChannelMember } from "@mail/core/common/channel_member_model";
import { removeFromArray } from "@mail/utils/common/arrays";

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
     * @param {Object|Array} data
     * @returns {ChannelMember}
     */
    insert(data) {
        const memberData = Array.isArray(data) ? data[1] : data;
        let member = this.store.ChannelMember.records[memberData.id];
        if (!member) {
            this.store.ChannelMember.records[memberData.id] = new ChannelMember();
            member = this.store.ChannelMember.records[memberData.id];
            member._store = this.store;
        }
        this.update(member, data);
        return member;
    }

    update(member, data) {
        const [command, memberData] = Array.isArray(data) ? data : ["insert", data];
        member.id = memberData.id;
        if ("persona" in memberData) {
            member.persona = this.store.Persona.insert({
                ...(memberData.persona.partner ?? memberData.persona.guest),
                type: memberData.persona.guest ? "guest" : "partner",
                country: memberData.persona.partner?.country,
                channelId: memberData.persona.guest ? memberData.channel.id : null,
            });
        }
        member.threadId = memberData.threadId ?? member.threadId ?? memberData.channel?.id;
        if (member.threadId && !member.thread) {
            this.store.Thread.insert({
                id: member.threadId,
                model: "discuss.channel",
            });
        }
        switch (command) {
            case "insert":
                {
                    if (member.thread && member.notIn(member.thread.channelMembers)) {
                        member.thread.channelMembers.push(member);
                    }
                }
                break;
            case "unlink":
                removeFromArray(this.store.ChannelMember.records, member);
            // eslint-disable-next-line no-fallthrough
            case "insert-and-unlink":
                if (member.thread) {
                    removeFromArray(member.thread.channelMembers, member);
                }
                break;
        }
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
