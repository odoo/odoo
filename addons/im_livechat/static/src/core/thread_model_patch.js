/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

patch(Thread, {
    insert(data) {
        const thread = super.insert(data);
        if (thread.type === "livechat") {
            if (data?.channel) {
                assignDefined(thread, data.channel, ["anonymous_name"]);
            }
            if (data?.operator_pid) {
                thread.operator = {
                    type: "partner",
                    id: data.operator_pid[0],
                    displayName: data.operator_pid[1],
                };
            }
            this.store.discuss.livechat.threads.add(thread);
            this.env.services["mail.thread"].sortChannels();
        }
        return thread;
    },
});

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.operator = Record.one("Persona");
    },
    get typesAllowingCalls() {
        return super.typesAllowingCalls.concat(["livechat"]);
    },

    get hasMemberList() {
        return this.type === "livechat" || super.hasMemberList;
    },

    get isChatChannel() {
        return this.type === "livechat" || super.isChatChannel;
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
        return this._store.env.services["mail.thread"].avatarUrl(this.correspondent, this);
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
