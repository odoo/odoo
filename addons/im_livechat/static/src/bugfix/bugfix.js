/**
 * This file allows introducing new JS modules without contaminating other files.
 * This is useful when bug fixing requires adding such JS modules in stable
 * versions of Odoo. Any module that is defined in this file should be isolated
 * in its own file in master.
 */
odoo.define('im_livechat/static/src/bugfix/bugfix.js', function (require) {
'use strict';

const {
    registerInstancePatchModel,
} = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.chat_window', 'im_livechat/static/src/models/chat_window/chat_window.js', {

    /**
     * @override
     */
    close({ notifyServer } = {}) {
        if (
            this.thread &&
            this.thread.model === 'mail.channel' &&
            this.thread.channel_type === 'livechat' &&
            this.thread.mainCache.isLoaded &&
            this.thread.messages.length === 0
        ) {
            notifyServer = true;
            this.thread.unpin();
        }
        this._super({ notifyServer });
    }
});

});
