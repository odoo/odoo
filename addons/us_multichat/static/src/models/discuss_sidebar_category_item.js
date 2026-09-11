/** @odoo-module **/

import { clear } from "@mail/model/model_field_command";
import { one } from "@mail/model/model_field";
import { registerPatch } from "@mail/model/model_core";


registerPatch({
    name: 'DiscussSidebarCategoryItem',
    fields: {
        avatarUrl: {
            compute() {
                if (this.channel?.channel_type?.startsWith("multi_livechat_")) {
                    if (this.channel.correspondent) {
                            return this.channel.correspondent.avatarUrl;
                    }
                }
                return this._super();
            },
        },
        categoryCounterContribution: {
            compute() {
                if (this.channel?.channel_type?.startsWith("multi_livechat_")) {
                    return this.channel.localMessageUnreadCounter > 0 ? 1 : 0;
                }
                return this._super();
            },
        },
        counter: {
            compute() {
                if (this.channel?.channel_type?.startsWith("multi_livechat_")) {
                    return this.channel.localMessageUnreadCounter;
                }
                return this._super();
            },
        },
        hasSettingsCommand: {
            compute() {
                if (this.channel?.channel_type?.startsWith("multi_livechat_")) {
                    return true;
                }
                return this._super();
            },
        },
    },
});