/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'NotificationGroupView',
    identifyingFields: ['notificationListViewOwner', 'notificationGroup'],
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
            this.notificationGroup.openDocuments();
            if (!this.messaging.device.isSmall) {
                this.messaging.messagingMenu.close();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickMarkAsRead(ev) {
            this.notificationGroup.notifyCancel();
        },
    },
    fields: {
        /**
         * Reference of the "mark as read" button. Useful to disable the
         * top-level click handler when clicking on this specific button.
         */
        markAsReadRef: attr(),
        notificationGroup: one('NotificationGroup', {
            inverse: 'notificationGroupViews',
            readonly: true,
            required: true,
        }),
        notificationListViewOwner: one('NotificationListView', {
            inverse: 'notificationGroupViews',
            readonly: true,
            required: true,
        }),
    },
});
