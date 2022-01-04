/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many2one } from '@mail/model/model_field';

registerModel({
    name: 'mail.notification_group_view',
    identifyingFields: ['notificationListViewOwner', 'notificationGroup'],
    fields: {
        notificationGroup: many2one('mail.notification_group', {
            inverse: 'notificationGroupViews',
            readonly: true,
            required: true,
        }),
        notificationListViewOwner: many2one('mail.notification_list_view', {
            inverse: 'notificationGroupViews',
            readonly: true,
            required: true,
        }),
    },
});
