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
                const convertedData = this.global.Messaging.models['Thread'].convertData(
                    Object.assign({ model: 'mail.channel' }, message.payload)
                );
                this.global.Messaging.models['Thread'].insert(convertedData);
                const channel = this.global.Messaging.models['Thread'].findFromIdentifyingData({
                    id: message.payload.id,
                    model: 'mail.channel',
                });
                this.global.ChatWindowManager.openThread(channel, {
                    makeActive: true,
                });
            }
            return this._super(message);
        },
    },
});
