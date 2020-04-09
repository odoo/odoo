odoo.define('im_livechat.messaging.component.ThreadPreview', function (require) {
'use strict';

const components = {
    ThreadPreview: require('mail.messaging.component.ThreadPreview'),
};

const { patch } = require('web.utils');

patch(components.ThreadPreview, 'im_livechat.messaging.component.ThreadPreview', {

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
