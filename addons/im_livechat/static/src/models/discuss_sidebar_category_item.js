/** @odoo-module **/

import { clear, Patch } from "@mail/model";

Patch({
    name: "DiscussSidebarCategoryItem",
    fields: {
        avatarUrl: {
            compute() {
                if (this.channel.channel_type === "livechat") {
                    if (this.channel.correspondent && !this.channel.correspondent.is_public) {
                        return this.channel.correspondent.avatarUrl;
                    }
                }
                return this._super();
            },
        },
        categoryCounterContribution: {
            compute() {
                if (this.channel.channel_type === "livechat") {
                    return this.channel.localMessageUnreadCounter > 0 ? 1 : 0;
                }
                return this._super();
            },
        },
        counter: {
            compute() {
                if (this.channel.channel_type === "livechat") {
                    return this.channel.localMessageUnreadCounter;
                }
                return this._super();
            },
        },
        hasUnpinCommand: {
            compute() {
                if (this.channel.channel_type === "livechat") {
                    return !this.channel.localMessageUnreadCounter;
                }
                return this._super();
            },
        },
        threadIconView: {
            compute() {
                if (this.channel.channel_type === "livechat") {
                    return clear();
                }
                return this._super();
            },
        },
    },
});
