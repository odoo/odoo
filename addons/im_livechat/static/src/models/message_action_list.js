/** @odoo-module **/

import { patchFields } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';
// ensure the model definition is loaded before the patch
import '@mail/models/message_action_list';

patchFields('MessageActionList', {
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
});
