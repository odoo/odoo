/** @odoo-module **/

import { clear, registerPatch } from '@mail/model';

registerPatch({
    name: 'MessageActionList',
    fields: {
        actionReplyTo: {
            compute() {
                if (
                    this.message &&
                    this.message.originThread &&
                    this.message.originThread.channel &&
                    this.message.originThread.channel.channel_type === 'livechat'
                ) {
                    return clear();
                }
                return this._super();
            }
        },
    },
});
