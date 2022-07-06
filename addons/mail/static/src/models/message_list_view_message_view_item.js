/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

/**
 * Models a relation between a message list view and a message view where
 * message is used as iterating field.
 */
registerModel({
    name: 'MessageListViewMessageViewItem',
    identifyingFields: ['messageListViewOwner', 'message'],
    fields: {
        isSquashed: attr({
            required: true,
        }),
        message: one('Message', {
            inverse: 'messageListViewMessageViewItems',
            readonly: true,
            required: true,
        }),
        messageListViewOwner: one('MessageListView', {
            inverse: 'messageListViewMessageViewItems',
            readonly: true,
            required: true,
        }),
        messageView: one('MessageView', {
            default: insertAndReplace(),
            inverse: 'messageListViewMessageViewItemOwner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
