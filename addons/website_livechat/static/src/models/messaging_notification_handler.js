/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'MessagingNotificationHandler',
    recordMethods: {
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
    },
});
