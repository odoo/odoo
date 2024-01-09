/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    _computeDiscussAppCategory() {
        return this.type === "livechat"
            ? this._store.discuss.livechat
            : super._computeDiscussAppCategory();
    },
    get hasMemberList() {
        return this.type === "livechat" || super.hasMemberList;
    },
    get canLeave() {
        return this.type !== "livechat" && super.canLeave;
    },
    get canUnpin() {
        if (this.type === "livechat") {
            return this.message_unread_counter === 0;
        }
        return super.canUnpin;
    },

    get correspondents() {
        return super.correspondents.filter((correspondent) => !correspondent.is_bot);
    },

    computeCorrespondent() {
        let correspondent = super.computeCorrespondent();
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

    get avatarUrl() {
        if (this.type === "livechat" && this.correspondent) {
            return this.correspondent.avatarUrl;
        }
        return super.avatarUrl;
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
