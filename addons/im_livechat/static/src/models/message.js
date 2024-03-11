/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'Message',
    fields: {
        hasReactionIcon: {
            compute() {
                if (this.originThread && this.originThread.channel && this.originThread.channel.channel_type === 'livechat') {
                    return false;
                }
                return this._super();
            },
        },
    },
});
