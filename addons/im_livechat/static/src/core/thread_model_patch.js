/* @odoo-module */

import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "im_livechat", {
    get isChannel() {
        return this.type === "livechat" || this._super();
    },

    get hasMemberList() {
        return this.type === "livechat" || this._super();
    },

    get isChatChannel() {
        return this.type === "livechat" || this._super();
    },

    get allowSetLastSeenMessage() {
        return this.type === "livechat" || this._super();
    },

    get allowReactions() {
        return this.type === "livechat" ? false : this._super();
    },

    get allowReplies() {
        return this.type === "livechat" ? false : this._super();
    },

    get correspondents() {
        return this._super().filter((correspondent) => !correspondent.is_bot);
    },

    get correspondent() {
        let correspondent = this._super();
        if (this.type === "livechat" && !correspondent) {
            // For livechat threads, the correspondent is the first
            // channel member that is not the operator.
            const orderedChannelMembers = [...this.channelMembers].sort((a, b) => a.id - b.id);
            const isFirstMemberOperator =
                orderedChannelMembers[0]?.persona.type === "partner" &&
                orderedChannelMembers[0]?.persona.id === this.operator.id;
            correspondent = isFirstMemberOperator
                ? orderedChannelMembers[1]?.persona
                : orderedChannelMembers[0]?.persona;
        }
        return correspondent;
    },

    get displayName() {
        if (this.type !== "livechat" || !this.correspondent) {
            return this._super();
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
            return this._super();
        }
        return this.correspondent && !this.correspondent.is_public
            ? `/web/image/res.partner/${this.correspondent.id}/avatar_128`
            : DEFAULT_AVATAR;
    },

    /**
     *
     * @param {import("@mail/core/common/persona_model").Persona} persona
     */
    getMemberName(persona) {
        if (this.type !== "livechat") {
            return this._super(persona);
        }
        if (persona.user_livechat_username) {
            return persona.user_livechat_username;
        }
        if (persona.is_public && this.anonymous_name) {
            return this.anonymous_name;
        }
        return this._super(persona);
    },
});
