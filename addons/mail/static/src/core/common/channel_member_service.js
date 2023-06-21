/* @odoo-module */

import { ChannelMember } from "@mail/core/common/channel_member_model";
import { removeFromArray } from "@mail/utils/common/arrays";

import { registry } from "@web/core/registry";
import { insertPersona } from "./persona_service";

let gEnv;
let store;

/**
 * @param {Object|Array} data
 * @returns {ChannelMember}
 */
export function insertChannelMember(data) {
    const memberData = Array.isArray(data) ? data[1] : data;
    let member = store.channelMembers[memberData.id];
    if (!member) {
        store.channelMembers[memberData.id] = new ChannelMember();
        member = store.channelMembers[memberData.id];
        member._store = store;
    }
    updateChannelMember(member, data);
    return member;
}

function updateChannelMember(member, data) {
    const [command, memberData] = Array.isArray(data) ? data : ["insert", data];
    member.id = memberData.id;
    if ("persona" in memberData) {
        member.persona = insertPersona({
            ...(memberData.persona.partner ?? memberData.persona.guest),
            type: memberData.persona.guest ? "guest" : "partner",
            country: memberData.persona.partner?.country,
            channelId: memberData.persona.guest ? memberData.channel.id : null,
        });
    }
    member.threadId = memberData.threadId ?? member.threadId ?? memberData.channel.id;
    if (!member.thread) {
        // this prevents cyclic dependencies between insertThread and discuss.channel.member
        gEnv.bus.trigger("mail.thread/insert", {
            id: member.threadId,
            model: "discuss.channel",
        });
    }
    switch (command) {
        case "insert":
            {
                if (!store.incl(member.thread.channelMembers, member)) {
                    member.thread.channelMembers.push(member);
                }
            }
            break;
        case "unlink":
            removeFromArray(store.channelMembers, member);
        // eslint-disable-next-line no-fallthrough
        case "insert-and-unlink":
            removeFromArray(member.thread.channelMembers, member);
            break;
    }
}

export class ChannelMemberService {
    constructor(env, services) {
        gEnv = env;
        store = services["mail.store"];
    }
}

export const channelMemberService = {
    dependencies: ["mail.store", "mail.persona"],
    start(env, services) {
        return new ChannelMemberService(env, services);
    },
};
registry.category("services").add("discuss.channel.member", channelMemberService);
