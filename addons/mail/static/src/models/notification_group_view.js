/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'NotificationGroupView',
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
            const messaging = this.messaging;
            this.notificationGroup.openDocuments();
            if (!messaging.device.isSmall) {
                messaging.messagingMenu.close();
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
        imageSrc: attr({
            compute() {
                if (this.notificationGroup.notification_type === 'email') {
                    return '/mail/static/src/img/smiley/mailfailure.jpg';
                }
                return clear();
            },
        }),
        /**
         * Reference of the "mark as read" button. Useful to disable the
         * top-level click handler when clicking on this specific button.
         */
        markAsReadRef: attr(),
        notificationGroup: one('NotificationGroup', {
            identifying: true,
            inverse: 'notificationGroupViews',
        }),
        notificationListViewOwner: one('NotificationListView', {
            identifying: true,
            inverse: 'notificationGroupViews',
        }),
    },
});
