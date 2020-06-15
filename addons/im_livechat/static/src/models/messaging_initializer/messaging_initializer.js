odoo.define('im_livechat/static/src/models/messaging_initializer/messaging_initializer.js', function (require) {
'use strict';

const { registerInstancePatchModel } = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.messaging_initializer', 'im_livechat/static/src/models/messaging_initializer/messaging_initializer.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     * @param {Object[]} [param0.channel_livechat=[]]
     */
    _initChannels(initMessagingData) {
        this._super(initMessagingData);
        const { channel_livechat = [] } = initMessagingData;
        for (const data of channel_livechat) {
            this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(data),
            );
        }
    },
});

});
