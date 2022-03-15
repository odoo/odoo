/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ThreadPreviewView',
    identifyingFields: ['notificationListViewOwner', 'thread'],
    fields: {
        notificationListViewOwner: one('NotificationListView', {
            inverse: 'threadPreviewViews',
            readonly: true,
            required: true,
        }),
        thread: one('Thread', {
            inverse: 'threadPreviewViews',
            readonly: true,
            required: true,
        }),
    },
});
