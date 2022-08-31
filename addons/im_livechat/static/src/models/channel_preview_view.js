/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/channel_preview_view';

patchRecordMethods('ChannelPreviewView', {
    /**
     * @override
     */
    _computeImageUrl() {
        if (this.channel.channel_type === 'livechat') {
            return '/mail/static/src/img/smiley/avatar.jpg';
        }
        return this._super();
    },
});
