/* @odoo-module */

import { reactive, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const OTHER_LONG_TYPING = 60000;

export class Typing {
    busService;
    /** @type {import("@mail/core/channel_member_service").ChannelMemberService} */
    channelMemberService;
    /** @type {Map<number, Set<number>>} */
    memberIdsByChannelId = new Map();
    /** @type {Map<number, number>} */
    timerByMemberId = new Map();
    /** @type {import("@mail/core/store_service").Store} */
    storeService;

    constructor({
        bus_service: busService,
        "discuss.channel.member": channelMemberService,
        "mail.store": storeService,
    }) {
        Object.assign(this, { busService, channelMemberService, storeService });
    }

    setup() {
        this.busService.subscribe("discuss.channel.member/typing_status", (payload) => {
            const member = this.channelMemberService.insert(payload);
            if (payload.isTyping) {
                this.addTypingMember(member);
            } else {
                this.removeTypingMember(member);
            }
        });
        this.busService.start();
    }

    /**
     * @param {import("@mail/core/channel_member_model").ChannelMember} member
     */
    addTypingMember(member) {
        if (!this.memberIdsByChannelId.has(member.thread.id)) {
            this.memberIdsByChannelId.set(member.thread.id, new Set());
        }
        const memberIds = this.memberIdsByChannelId.get(member.thread.id);
        memberIds.add(member.id);
        browser.clearTimeout(this.timerByMemberId.get(member.id));
        this.timerByMemberId.set(
            member.id,
            browser.setTimeout(() => this.removeTypingMember(member), OTHER_LONG_TYPING)
        );
    }

    /**
     * @param {import("@mail/core/thread_model").Thread} channel
     * @returns {import("@mail/core/channel_member_model").ChannelMember[]}
     */
    getTypingMembers(channel) {
        return [...(this.memberIdsByChannelId.get(channel.id) ?? new Set())]
            .map((id) => this.channelMemberService.insert({ id }))
            .filter((member) => member.persona !== this.storeService.self);
    }

    /**
     * @param {import("@mail/core/thread_model").Thread} channel
     * @returns {boolean}
     */
    hasTypingMembers(channel) {
        return this.getTypingMembers(channel).length > 0;
    }

    /**
     * @param {import("@mail/core/channel_member_model").ChannelMember} member
     */
    removeTypingMember(member) {
        const memberIds = this.memberIdsByChannelId.get(member.thread.id);
        if (memberIds) {
            memberIds.delete(member.id);
            if (memberIds.size === 0) {
                this.memberIdsByChannelId.delete(member.thread.id);
            }
        }
        browser.clearTimeout(this.timerByMemberId.get(member.id));
        this.timerByMemberId.delete(member.id);
    }
}

export const discussTypingService = {
    dependencies: ["bus_service", "discuss.channel.member", "mail.store"],
    start(env, services) {
        const typing = reactive(new Typing(services));
        typing.setup();
        return typing;
    },
};

registry.category("services").add("discuss.typing", discussTypingService);

/**
 * @returns {Typing}
 */
export function useTypingService() {
    return useState(useService("discuss.typing"));
}
