/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadNeedactionPreviewView',
    identifyingFields: ['notificationListViewOwner', 'thread'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageAuthorPrefixView() {
            if (
                this.thread.lastNeedactionMessageAsOriginThread &&
                this.thread.lastNeedactionMessageAsOriginThread.author
            ) {
                return insertAndReplace();
            }
            return clear();
        },
    },
    fields: {
        /**
         * Reference of the "mark as read" button. Useful to disable the
         * top-level click handler when clicking on this specific button.
         */
        markAsReadRef: attr(),
        messageAuthorPrefixView: one('MessageAuthorPrefixView', {
            compute: '_computeMessageAuthorPrefixView',
            inverse: 'threadNeedactionPreviewViewOwner',
            isCausal: true,
        }),
        notificationListViewOwner: one('NotificationListView', {
            inverse: 'threadNeedactionPreviewViews',
            readonly: true,
            required: true,
        }),
        thread: one('Thread', {
            inverse: 'threadNeedactionPreviewViews',
            readonly: true,
            required: true,
        }),
    },
});
