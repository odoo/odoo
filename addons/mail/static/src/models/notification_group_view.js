/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'NotificationGroupView',
    identifyingFields: ['notificationListViewOwner', 'notificationGroup'],
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
