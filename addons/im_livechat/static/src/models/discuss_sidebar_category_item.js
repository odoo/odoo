/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'DiscussSidebarCategoryItem',
    fields: {
        avatarUrl: {
            compute() {
                if (this.channel.channel_type === 'livechat') {
                    if (this.channel.correspondent && !this.channel.correspondent.is_public) {
                        return this.channel.correspondent.avatarUrl;
                    }
                }
                return this._super();
            },
        },
        categoryCounterContribution: {
            compute() {
                if (this.channel.channel_type === 'livechat') {
                    return this.channel.localMessageUnreadCounter > 0 ? 1 : 0;
                }
                return this._super();
            },
        },
        counter: {
            compute() {
                if (this.channel.channel_type === 'livechat') {
                    return this.channel.localMessageUnreadCounter;
                }
                return this._super();
            },
        },
        hasThreadIcon: {
            compute() {
                if (this.channel.channel_type === 'livechat') {
                    return clear();
                }
                return this._super();
            },
        },
        hasUnpinCommand: {
            compute() {
                if (this.channel.channel_type === 'livechat') {
                    return !this.channel.localMessageUnreadCounter;
                }
                return this._super();
            },
        },
    },
});
