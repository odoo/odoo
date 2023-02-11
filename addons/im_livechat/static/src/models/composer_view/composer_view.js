/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';

registerInstancePatchModel('mail.composer_view', 'im_livechat/static/src/models/composer_view/composer_view.js', {

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
