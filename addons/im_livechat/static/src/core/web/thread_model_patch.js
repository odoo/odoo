/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { assignIn } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

patch(Thread, {
    _insert(data) {
        const thread = super._insert(...arguments);
        if (thread.type === "livechat") {
            assignIn(thread, data, ["anonymous_name", "anonymous_country"]);
            this.store.discuss.livechat.threads.add(thread);
            this.env.services["mail.thread"].sortChannels();
        }
        return thread;
    },
});

patch(Thread.prototype, {
    get hasMemberList() {
        return this.type === "livechat" || super.hasMemberList;
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
        if (this.anonymous_country) {
            return `${this.getMemberName(this.correspondent)} (${this.anonymous_country.name})`;
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
