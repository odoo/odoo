/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'NotificationGroupView',
    identifyingFields: ['notificationListViewOwner', 'notificationGroup'],
    fields: {
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
