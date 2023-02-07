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
        const correspondentName =
            this.correspondent.user_livechat_username ||
            this.anonymous_name ||
            this.correspondent.name;
        if (!this.correspondent.is_public && this.correspondent.country) {
            return `${correspondentName} (${this.correspondent.country.name})`;
        }
        if (this.anonymous_country) {
            return `${correspondentName} (${this.anonymous_country.name})`;
        }
        return correspondentName;
    },
});
