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
    async _initChannels(initMessagingData) {
        await this.async(() => this._super(initMessagingData));
        const { channel_livechat = [] } = initMessagingData;
        for (const data of channel_livechat) {
            // there might be a lot of channels, insert each of them one by
            // one asynchronously to avoid blocking the UI
            await this.async(() => new Promise(resolve => setTimeout(resolve)));
            this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(data),
            );
        }
    },
});

});
