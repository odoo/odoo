/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'NotificationMessageView',
    fields: {
        message: one('Message', {
            related: 'messageListViewItemOwner.message',
            inverse: 'notificationMessageViews',
            required: true,
        }),
        messageListViewItemOwner: one('MessageListViewItem', {
            identifying: true,
            inverse: 'notificationMessageView',
        }),
    },
});
