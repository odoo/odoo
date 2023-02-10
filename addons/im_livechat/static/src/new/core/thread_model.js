/** @odoo-module */

import { Thread } from "@mail/new/core/thread_model";
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

    get displayName() {
        if (this.type !== "livechat" || !this.correspondent) {
            return this._super();
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
        if (this.type === "livechat" && !this.correspondent.is_public) {
            return `/web/image/res.partner/${this.correspondent.id}/avatar_128`;
        }
        return this._super();
    },

    /**
     *
     * @param {import("@mail/new/core/persona_model").Persona} persona
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
