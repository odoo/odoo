/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';
import '@mail/models/composer_view';

patchRecordMethods('ComposerView', {
    /**
     * @override
     */
    _computeDropZoneView() {
        if (this.composer && this.composer.thread && this.composer.thread.channel && this.composer.thread.channel.channel_type === 'livechat') {
            return clear();
        }
        return this._super();
    },
});
