/* @odoo-module */

import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

patch(Thread, {
    insert(data) {
        const isUnknown = !this.get(data);
        const thread = super.insert(data);
        if (thread.type === "livechat") {
            if (data?.channel) {
                assignDefined(thread, data.channel, ["anonymous_name"]);
            }
            if (data?.operator_pid) {
                thread.operator = this.store.Persona.insert({
                    type: "partner",
                    id: data.operator_pid[0],
                    displayName: data.operator_pid[1],
                });
            }
            if (isUnknown) {
                this.store.discuss.livechat.threads.push(thread.localId);
                this.env.services["mail.thread"].sortChannels();
            }
        }
        return thread;
    },
});

patch(Thread.prototype, {
    get typesAllowingCalls() {
        return super.typesAllowingCalls.concat(["livechat"]);
    },

    get isChannel() {
        return this.type === "livechat" || super.isChannel;
    },

    get hasMemberList() {
        return this.type === "livechat" || super.hasMemberList;
    },

    get isChatChannel() {
        return this.type === "livechat" || super.isChatChannel;
    },

    get allowSetLastSeenMessage() {
        return this.type === "livechat" || super.allowSetLastSeenMessage;
    },

    get correspondents() {
        return super.correspondents.filter((correspondent) => !correspondent.is_bot);
    },

    get correspondent() {
        let correspondent = super.correspondent;
        if (this.type === "livechat" && !correspondent) {
            // For livechat threads, the correspondent is the first
            // channel member that is not the operator.
            const orderedChannelMembers = [...this.channelMembers].sort((a, b) => a.id - b.id);
            const isFirstMemberOperator = orderedChannelMembers[0]?.persona.eq(this.operator);
            correspondent = isFirstMemberOperator
                ? orderedChannelMembers[1]?.persona
                : orderedChannelMembers[0]?.persona;
        }
        return correspondent;
    },

    get displayName() {
        if (this.type !== "livechat" || !this.correspondent) {
            return super.displayName;
        }
        if (!this.correspondent.is_public && this.correspondent.country) {
            return `${this.getMemberName(this.correspondent)} (${this.correspondent.country.name})`;
        }
        if (this.channel?.anonymous_country) {
            return `${this.getMemberName(this.correspondent)} (${
                this.channel.anonymous_country.name
            })`;
        }
        return this.getMemberName(this.correspondent);
    },

    get imgUrl() {
        if (this.type !== "livechat") {
            return super.imgUrl;
        }
        return this.correspondent && this.correspondent.type !== "guest"
            ? `/web/image/res.partner/${this.correspondent.id}/avatar_128`
            : DEFAULT_AVATAR;
    },

    /**
     *
     * @param {import("models").Persona} persona
     */
    getMemberName(persona) {
        if (this.type !== "livechat") {
            return super.getMemberName(persona);
        }
        if (persona.user_livechat_username) {
            return persona.user_livechat_username;
        }
        return super.getMemberName(persona);
    },
});
