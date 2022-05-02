/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'NotificationRequestView',
    identifyingFields: ['NotificationRequestView/notificationListViewOwner'],
    fields: {
        notificationListViewOwner: one('NotificationListView', {
            inverse: 'notificationRequestView',
            required: true,
            readonly: true,
        }),
    },
});
