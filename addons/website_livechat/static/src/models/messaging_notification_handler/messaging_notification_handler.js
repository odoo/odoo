/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging_notification_handler/messaging_notification_handler';

patchRecordMethods('MessagingNotificationHandler', {
    /**
     * @override
     */
    async _handleNotification(message) {
        if (message.type === 'website_livechat.send_chat_request') {
            const convertedData = this.messaging.models['Thread'].convertData(
                Object.assign({ model: 'mail.channel' }, message.payload)
            );
            this.messaging.models['Thread'].insert(convertedData);
            const channel = this.messaging.models['Thread'].findFromIdentifyingData({
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
