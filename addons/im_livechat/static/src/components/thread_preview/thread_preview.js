odoo.define('im_livechat/static/src/components/thread_preview/thread_preview.js', function (require) {
'use strict';

const components = {
    ThreadPreview: require('mail/static/src/components/thread_preview/thread_preview.js'),
};

const { patch } = require('web.utils');

patch(components.ThreadPreview, 'im_livechat/static/src/components/thread_preview/thread_preview.js', {

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
