/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';

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
