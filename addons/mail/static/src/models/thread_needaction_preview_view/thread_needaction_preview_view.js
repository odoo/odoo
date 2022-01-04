/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many2one } from '@mail/model/model_field';

registerModel({
    name: 'ThreadNeedactionPreviewView',
    identifyingFields: ['notificationListViewOwner', 'thread'],
    fields: {
        notificationListViewOwner: many2one('NotificationListView', {
            inverse: 'threadNeedactionPreviewViews',
            readonly: true,
            required: true,
        }),
        thread: many2one('Thread', {
            inverse: 'threadNeedactionPreviewViews',
            readonly: true,
            required: true,
        }),
    },
});
