/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadPreviewView',
    identifyingFields: ['notificationListViewOwner', 'thread'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageAuthorPrefixView() {
            if (
                this.thread.lastMessage &&
                this.thread.lastMessage.author
            ) {
                return insertAndReplace();
            }
            return clear();
        },
    },
    fields: {
        messageAuthorPrefixView: one('MessageAuthorPrefixView', {
            compute: '_computeMessageAuthorPrefixView',
            inverse: 'threadPreviewViewOwner',
            isCausal: true,
        }),
        notificationListViewOwner: one('NotificationListView', {
            inverse: 'threadPreviewViews',
            readonly: true,
            required: true,
        }),
        thread: one('Thread', {
            inverse: 'threadPreviewViews',
            readonly: true,
            required: true,
        }),
    },
});
