/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';

registerModel({
    name: 'NotificationRequestView',
    identifyingFields: ['notificationListViewOwner'],
    fields: {
        notificationListViewOwner: one2one('NotificationListView', {
            inverse: 'notificationRequestView',
            required: true,
            readonly: true,
        }),
    },
});
