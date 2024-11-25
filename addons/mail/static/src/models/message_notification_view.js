/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'NotificationMessageView',
    recordMethods: {
        onComponentUpdate() {
            if (!this.exists()) {
                return;
            }
            if (this.messageListViewItemOwner.threadViewOwnerAsLastMessageListViewItem && this.messageListViewItemOwner.isPartiallyVisible()) {
                this.messageListViewItemOwner.threadViewOwnerAsLastMessageListViewItem.handleVisibleMessage(this.message);
            }
        },
        async onClick(ev) {
            await this.messaging.handleClickOnLink(ev);
        },
    },
    fields: {
        component: attr(),
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
