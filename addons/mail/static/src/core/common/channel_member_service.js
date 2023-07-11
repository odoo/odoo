/* @odoo-module */

import { ChannelMember } from "@mail/core/common/channel_member_model";
import { removeFromArray } from "@mail/utils/common/arrays";

import { registry } from "@web/core/registry";

export class ChannelMemberService {
    constructor(env, { "mail.store": store, "mail.persona": personaService }) {
        this.env = env;
        this.store = store;
        this.personaService = personaService;
    }

    /**
     * @param {Object|Array} data
     * @returns {ChannelMember}
     */
    insert(data) {
        const memberData = Array.isArray(data) ? data[1] : data;
        let member = this.store.channelMembers[memberData.id];
        if (!member) {
            this.store.channelMembers[memberData.id] = new ChannelMember();
            member = this.store.channelMembers[memberData.id];
            member._store = this.store;
        }
        this.update(member, data);
        return member;
    }

    update(member, data) {
        const [command, memberData] = Array.isArray(data) ? data : ["insert", data];
        member.id = memberData.id;
        if ("persona" in memberData) {
            member.persona = this.personaService.insert({
                ...(memberData.persona.partner ?? memberData.persona.guest),
                type: memberData.persona.guest ? "guest" : "partner",
                country: memberData.persona.partner?.country,
                channelId: memberData.persona.guest ? memberData.channel.id : null,
            });
        }
        member.threadId = memberData.threadId ?? member.threadId ?? memberData.channel?.id;
        if (member.threadId && !member.thread) {
            // this prevents cyclic dependencies between mail.thread and discuss.channel.member
            this.env.bus.trigger("mail.thread/insert", {
                id: member.threadId,
                model: "discuss.channel",
            });
        }
        switch (command) {
            case "insert":
                {
                    if (member.thread && !member.thread.channelMembers.includes(member)) {
                        member.thread.channelMembers.push(member);
                    }
                }
                break;
            case "unlink":
                removeFromArray(this.store.channelMembers, member);
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
    dependencies: ["mail.store", "mail.persona"],
    start(env, services) {
        return new ChannelMemberService(env, services);
    },
};
registry.category("services").add("discuss.channel.member", channelMemberService);
