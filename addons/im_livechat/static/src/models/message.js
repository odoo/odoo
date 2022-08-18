/** @odoo-module **/

import { patchModelMethods, patchRecordMethods } from '@mail/model/model_core';
// ensure the model definition is loaded before the patch
import '@mail/models/message';

patchModelMethods('Message', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('author_id' in data) {
            if (data.author_id[2]) {
                // flux specific for livechat, a 3rd param is livechat_username
                // and means 2nd param (display_name) should be ignored
                data2.author = {
                    id: data.author_id[0],
                    livechat_username: data.author_id[2],
                };
            }
        }
        return data2;
    },
});
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
