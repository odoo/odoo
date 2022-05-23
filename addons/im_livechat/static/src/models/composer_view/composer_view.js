/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import '@mail/models/composer_view/composer_view';

patchRecordMethods('ComposerView', {
    /**
     * @override
     */
    _computeHasDropZone() {
        if (this.composer.thread && this.composer.thread.channel_type === 'livechat') {
            return false;
        }
        return this._super();
    },
});
