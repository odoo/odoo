/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

/**
 * Models a relation between a message list view and a message view where
 * message is used as iterating field.
 */
registerModel({
    name: 'MessageListViewMessageViewItem',
    fields: {
        isSquashed: attr({
            required: true,
        }),
        message: one('Message', {
            identifying: true,
            inverse: 'messageListViewMessageViewItems',
        }),
        messageListViewOwner: one('MessageListView', {
            identifying: true,
            inverse: 'messageListViewMessageViewItems',
        }),
        messageView: one('MessageView', {
            default: {},
            inverse: 'messageListViewMessageViewItemOwner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
