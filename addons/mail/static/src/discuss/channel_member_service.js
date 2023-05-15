/** @odoo-module */

import { registry } from "@web/core/registry";
import { removeFromArray } from "@mail/utils/arrays";
import { ChannelMember } from "./channel_member_model";

export class ChannelMemberService {
    constructor(
        env,
        { "mail.store": store, "mail.persona": personaService, "discuss.store": discussStore }
    ) {
        Object.assign(this, { store, discussStore, personaService });
        this.env = env;
    }

    /**
     * @param {Object|Array} data
     * @returns {ChannelMember}
     */
    insert(data) {
        const memberData = Array.isArray(data) ? data[1] : data;
        let member = this.discussStore.channelMembers[memberData.id];
        if (!member) {
            this.discussStore.channelMembers[memberData.id] = new ChannelMember();
            member = this.discussStore.channelMembers[memberData.id];
            member._store = this.discussStore;
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
        member.channelId = memberData.channelId ?? member.channelId ?? memberData.channel.id;
        if (!member.channel) {
            // this prevents cyclic dependencies between mail.thread and discuss.channel.member
            this.env.bus.trigger("mail.thread/insert", {
                id: member.channelId,
                model: "discuss.channel",
            });
        }
        switch (command) {
            case "insert":
                {
                    if (!member.channel.channelMembers.includes(member)) {
                        member.channel.channelMembers.push(member);
                    }
                }
                break;
            case "unlink":
                removeFromArray(this.discussStore.channelMembers, member);
            // eslint-disable-next-line no-fallthrough
            case "insert-and-unlink":
                removeFromArray(member.channel.channelMembers, member);
                break;
        }
    }
}

export const channelMemberService = {
    dependencies: ["mail.store", "mail.persona", "discuss.store"],
    start(env, services) {
        return new ChannelMemberService(env, services);
    },
};
registry.category("services").add("discuss.channel.member", channelMemberService);
