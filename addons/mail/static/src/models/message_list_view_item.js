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
         * Tell whether the item is partially visible on browser window or not.
         *
         * @returns {boolean}
         */
        isPartiallyVisible() {
            const itemView = this.messageView || this.notificationMessageView;
            if (!itemView || !itemView.component || !itemView.component.root.el) {
                return false;
            }
            const elRect = itemView.component.root.el.getBoundingClientRect();
            if (!itemView.component.root.el.parentNode) {
                return false;
            }
            const parentRect = itemView.component.root.el.parentNode.getBoundingClientRect();
            // intersection with 5px offset
            return (
                elRect.top < parentRect.bottom + 5 &&
                parentRect.top < elRect.bottom + 5
            );
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
            compute() {
                if (
                    this.message &&
                    this.message.originThread &&
                    this.message.originThread.channel &&
                    this.message.message_type === 'notification'
                ) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageListViewItemOwner',
        }),
        messageView: one('MessageView', {
            compute() {
                if (
                    this.message &&
                    this.message.originThread &&
                    !this.message.originThread.channel ||
                    this.message.message_type !== 'notification'
                ) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageListViewItemOwner',
        }),
        /**
         * States whether this message list view item is the last one of its thread view.
         * Computed from inverse relation.
         */
        threadViewOwnerAsLastMessageListViewItem: one('ThreadView', {
            inverse: 'lastMessageListViewItem',
            readonly: true,
        }),
    },
});
