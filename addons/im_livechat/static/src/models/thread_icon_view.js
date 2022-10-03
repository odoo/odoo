/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'ThreadIconView',
    fields: {
        threadTypingIconView: {
            compute() {
                if (
                    this.thread.channel &&
                    this.thread.channel.channel_type === 'livechat' &&
                    this.thread.orderedOtherTypingMembers.length > 0
                ) {
                    return {};
                }
                return this._super();
            },
        },
    },
});
