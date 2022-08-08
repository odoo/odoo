/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure the model definition is loaded before the patch
import '@mail/models/message_action_list';

patchRecordMethods('MessageActionList', {
    /**
     * @override
     */
    _computeHasReplyIcon() {
        if (
            this.message &&
            this.message.originThread &&
            this.message.originThread.channel &&
            this.message.originThread.channel.channel_type === 'livechat'
        ) {
            return false;
        }
        return this._super();
    }
});
