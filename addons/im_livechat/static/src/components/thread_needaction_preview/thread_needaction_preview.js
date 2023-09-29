odoo.define('im_livechat/static/src/components/thread_needaction_preview/thread_needaction_preview.js', function (require) {
'use strict';

const components = {
    ThreadNeedactionPreview: require('mail/static/src/components/thread_needaction_preview/thread_needaction_preview.js'),
};

const { patch } = require('web.utils');

patch(components.ThreadNeedactionPreview, 'thread_needaction_preview', {

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

});
