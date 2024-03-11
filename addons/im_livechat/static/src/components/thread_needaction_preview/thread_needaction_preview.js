/** @odoo-module **/

import { ThreadNeedactionPreview } from '@mail/components/thread_needaction_preview/thread_needaction_preview';

import { patch } from 'web.utils';

const components = { ThreadNeedactionPreview };

patch(components.ThreadNeedactionPreview.prototype, 'thread_needaction_preview', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    image(...args) {
        if (this.threadNeedactionPreviewView.thread.channel && this.threadNeedactionPreviewView.thread.channel.channel_type === 'livechat') {
            return '/mail/static/src/img/smiley/avatar.jpg';
        }
        return this._super(...args);
    }

});
