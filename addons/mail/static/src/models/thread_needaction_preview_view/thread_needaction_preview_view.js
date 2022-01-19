/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ThreadNeedactionPreviewView',
    identifyingFields: ['notificationListViewOwner', 'thread'],
    fields: {
        notificationListViewOwner: one('NotificationListView', {
            inverse: 'threadNeedactionPreviewViews',
            readonly: true,
            required: true,
        }),
        thread: one('Thread', {
            inverse: 'threadNeedactionPreviewViews',
            readonly: true,
            required: true,
        }),
    },
});
