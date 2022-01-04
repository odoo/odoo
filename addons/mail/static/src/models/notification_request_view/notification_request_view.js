/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';

registerModel({
    name: 'mail.notification_request_view',
    identifyingFields: ['notificationListViewOwner'],
    fields: {
        notificationListViewOwner: one2one('mail.notification_list_view', {
            inverse: 'notificationRequestView',
            required: true,
            readonly: true,
        }),
    },
});
