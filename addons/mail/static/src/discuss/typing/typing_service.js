/* @odoo-module */

import { reactive, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const OTHER_LONG_TYPING = 60000;

/**
 * @typedef TypingState
 * @property {Map<number, Set<number>>} memberIdsByChannelId
 * @property {Map<number, number>} timerByMemberId
 */
export class Typing {
    busService;
    /** @type {import("@mail/core/channel_member_service").ChannelMemberService} */
    channelMemberService;
    /** @type {TypingState} */
    state = reactive({
        memberIdsByChannelId: new Map(),
        timerByMemberId: new Map(),
    });
    /** @type {import("@mail/core/store_service").Store} */
    storeService;

    constructor({
        bus_service: busService,
        "discuss.channel.member": channelMemberService,
        "mail.store": storeService,
    }) {
        Object.assign(this, { busService, channelMemberService, storeService });
        this.setup();
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
        if (!this.state.memberIdsByChannelId.has(member.thread.id)) {
            this.state.memberIdsByChannelId.set(member.thread.id, new Set());
        }
        const memberIds = this.state.memberIdsByChannelId.get(member.thread.id);
        memberIds.add(member.id);
        browser.clearTimeout(this.state.timerByMemberId.get(member.id));
        this.state.timerByMemberId.set(
            member.id,
            browser.setTimeout(() => this.removeTypingMember(member), OTHER_LONG_TYPING)
        );
    }

    /**
     * @param {TypingState} state
     * @param {import("@mail/core/thread_model").Thread} channel
     * @returns {import("@mail/core/channel_member_model").ChannelMember[]}
     */
    getTypingMembers(state, channel) {
        return [...(state.memberIdsByChannelId.get(channel.id) ?? new Set())]
            .map((id) => this.channelMemberService.insert({ id }))
            .filter((member) => member.persona !== this.storeService.self);
    }

    /**
     * @param {TypingState} state
     * @param {import("@mail/core/thread_model").Thread} channel
     * @returns {boolean}
     */
    hasTypingMembers(state, channel) {
        return this.getTypingMembers(state, channel).length > 0;
    }

    /**
     * @param {import("@mail/core/channel_member_model").ChannelMember} member
     */
    removeTypingMember(member) {
        const memberIds = this.state.memberIdsByChannelId.get(member.thread.id);
        if (memberIds) {
            memberIds.delete(member.id);
            if (memberIds.size === 0) {
                this.state.memberIdsByChannelId.delete(member.thread.id);
            }
        }
        browser.clearTimeout(this.state.timerByMemberId.get(member.id));
        this.state.timerByMemberId.delete(member.id);
    }
}

export const discussTypingService = {
    dependencies: ["bus_service", "discuss.channel.member", "mail.store"],
    start(env, services) {
        return new Typing(services);
    },
};

registry.category("services").add("discuss.typing", discussTypingService);

// wrapper to ensure service getters receive the reactive state of the component
export function useTypingService() {
    /** @type {Typing} */
    const typingService = useService("discuss.typing");
    const state = useState(typingService.state);
    return {
        /**
         * @param {import("@mail/core/thread_model").Thread} channel
         * @returns {import("@mail/core/channel_member_model").ChannelMember[]}
         */
        getTypingMembers(channel) {
            return typingService.getTypingMembers(state, channel);
        },
        /**
         * @param {import("@mail/core/thread_model").Thread} channel
         * @returns {boolean}
         */
        hasTypingMembers(channel) {
            return typingService.hasTypingMembers(state, channel);
        },
    };
}
