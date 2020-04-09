odoo.define('im_livechat.messaging.entity.Thread', function (require) {
'use strict';

const { registerClassPatchEntity } = require('mail.messaging.entity.core');

registerClassPatchEntity('Thread', 'im_livechat.messaging.entity.Thread', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @static
     * @returns {mail.messaging.entity.Thread[]}
     */
    allOrderedAndPinnedLivechats() {
        return this.allPinnedChannels.filter(channel => channel.channel_type === 'livechat');
    }

});

});
