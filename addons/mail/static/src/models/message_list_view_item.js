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
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotificationMessageView() {
            if (this.message.message_type === 'notification' && this.message.originThread.channel) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageView() {
            if (this.message.message_type !== 'notification' || !this.message.originThread.channel) {
                return {};
            }
            return clear();
        },
    },
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
            compute: '_computeNotificationMessageView',
            inverse: 'messageListViewItemOwner',
            isCausal: true,
        }),
        messageView: one('MessageView', {
            compute: '_computeMessageView',
            inverse: 'messageListViewItemOwner',
            isCausal: true,
        }),
    },
});
