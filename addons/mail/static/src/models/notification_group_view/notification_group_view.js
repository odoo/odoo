/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many2one } from '@mail/model/model_field';

registerModel({
    name: 'NotificationGroupView',
    identifyingFields: ['notificationListViewOwner', 'notificationGroup'],
    fields: {
        notificationGroup: many2one('NotificationGroup', {
            inverse: 'notificationGroupViews',
            readonly: true,
            required: true,
        }),
        notificationListViewOwner: many2one('NotificationListView', {
            inverse: 'notificationGroupViews',
            readonly: true,
            required: true,
        }),
    },
});
