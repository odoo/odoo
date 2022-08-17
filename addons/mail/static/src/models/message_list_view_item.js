/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

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
        messageView: one('MessageView', {
            default: {},
            inverse: 'messageListViewItemOwner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
