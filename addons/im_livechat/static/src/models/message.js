/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure the model definition is loaded before the patch
import '@mail/models/message';

patchRecordMethods('Message', {
    /**
     * @override
     */
    _computeHasReactionIcon() {
        if (this.originThread && this.originThread.channel && this.originThread.channel.channel_type === 'livechat') {
            return false;
        }
        return this._super();
    },
});
