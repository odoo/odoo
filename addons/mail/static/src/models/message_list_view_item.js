/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

/**
 * Models a relation between a message list view and a message view where
 * message is used as iterating field.
 */
registerModel({
    name: 'MessageListViewItem',
    fields: {
        isSquashed: attr({
            required: true,
        }),
        message: one('Message', {
            identifying: true,
            inverse: 'messageListViewItems',
        }),
        messageListViewOwner: one('MessageListView', {
            identifying: true,
            inverse: 'messageListViewItems',
        }),
        notificationMessageView: one('NotificationMessageView', {
            compute() {
                if (this.message.message_type === 'notification' && this.message.originThread.channel) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageListViewItemOwner',
        }),
        messageView: one('MessageView', {
            compute() {
                if (this.message.message_type !== 'notification' || !this.message.originThread.channel) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageListViewItemOwner',
        }),
    },
});
