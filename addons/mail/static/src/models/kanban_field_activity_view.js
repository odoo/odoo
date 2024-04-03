/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'KanbanFieldActivityView',
    fields: {
        activityButtonView: one('ActivityButtonView', {
            default: {},
            inverse: 'kanbanFieldActivityViewOwner',
            required: true,
        }),
        id: attr({
            identifying: true,
        }),
        thread: one('Thread', {
            required: true,
        }),
        webRecord: attr({
            required: true,
        }),
    },
});
