/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadNeedactionPreviewView',
    identifyingFields: ['notificationListViewOwner', 'thread'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (!this.exists()) {
                return;
            }
            const markAsRead = this.markAsReadRef.el;
            if (markAsRead && markAsRead.contains(ev.target)) {
                // handled in `_onClickMarkAsRead`
                return;
            }
            this.thread.open();
            if (!this.messaging.device.isSmall) {
                this.messaging.messagingMenu.close();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickMarkAsRead(ev) {
            this.messaging.models['Message'].markAllAsRead([
                ['model', '=', this.thread.model],
                ['res_id', '=', this.thread.id],
            ]);
        },
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
