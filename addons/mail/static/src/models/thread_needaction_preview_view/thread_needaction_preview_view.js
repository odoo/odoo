/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many2one } from '@mail/model/model_field';

registerModel({
    name: 'mail.thread_needaction_preview_view',
    identifyingFields: ['notificationListViewOwner', 'thread'],
    fields: {
        notificationListViewOwner: many2one('mail.notification_list_view', {
            inverse: 'threadNeedactionPreviewViews',
            readonly: true,
            required: true,
        }),
        thread: many2one('mail.thread', {
            inverse: 'threadNeedactionPreviewViews',
            readonly: true,
            required: true,
        }),
    },
});
