/** @odoo-module **/

import { ThreadPreview } from '@mail/components/thread_preview/thread_preview';

import { patch } from 'web.utils';

const components = { ThreadPreview };

patch(components.ThreadPreview.prototype, 'im_livechat/static/src/components/thread_preview/thread_preview.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    image(...args) {
        if (this.thread.channel_type === 'livechat') {
            return '/mail/static/src/img/smiley/avatar.jpg';
        }
        return this._super(...args);
    }

});
