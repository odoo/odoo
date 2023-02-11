/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';

registerInstancePatchModel('mail.messaging_notification_handler', 'website_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    async _handleNotification(message) {
        if (message.type === 'website_livechat.send_chat_request') {
            const convertedData = this.messaging.models['mail.thread'].convertData(
                Object.assign({ model: 'mail.channel' }, message.payload)
            );
            this.messaging.models['mail.thread'].insert(convertedData);
            const channel = this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: message.payload.id,
                model: 'mail.channel',
            });
            this.messaging.chatWindowManager.openThread(channel, {
                makeActive: true,
            });
        }
        return this._super(message);
    },
});
