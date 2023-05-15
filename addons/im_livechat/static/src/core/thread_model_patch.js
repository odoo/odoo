/** @odoo-module */

import { Thread } from "@mail/core/thread_model";
import { createLocalId } from "@mail/utils/misc";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "im_livechat", {
    setup() {
        this._super();
        /** @type {import("@mail/discuss/discuss_store_service").Discusstore} */
        this.discussStore = this._store.env.services["discuss.store"];
    },

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

    get discussChannel() {
        return this.discussStore.channels[createLocalId("discuss.channel", this.id)];
    },

    get displayName() {
        if (this.type !== "livechat" || !this.discussChannel.correspondent) {
            return this._super();
        }
        if (
            !this.discussChannel.correspondent.is_public &&
            this.discussChannel.correspondent.country
        ) {
            return `${this.getMemberName(this.discussChannel.correspondent)} (${
                this.discussChannel.correspondent.country.name
            })`;
        }
        if (this.anonymous_country) {
            return `${this.getMemberName(this.discussChannel.correspondent)} (${
                this.anonymous_country.name
            })`;
        }
        return this.getMemberName(this.discussChannel.correspondent);
    },

    get imgUrl() {
        if (
            this.type === "livechat" &&
            this.discussChannel.correspondent &&
            !this.discussChannel.correspondent.is_public
        ) {
            return `/web/image/res.partner/${this.discussChannel.correspondent.id}/avatar_128`;
        }
        return this._super();
    },

    /**
     *
     * @param {import("@mail/core/persona_model").Persona} persona
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
