/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread_needaction_preview_view';

patchRecordMethods('ThreadNeedactionPreviewView', {
    /**
     * @override
     */
    _computeImageUrl() {
        if (!this.thread.channel || this.thread.channel.channel_type === 'livechat') {
            return clear();
        }
        return this._super();
    },
});
