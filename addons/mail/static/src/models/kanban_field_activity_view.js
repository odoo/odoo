/** @odoo-module **/

import { attr, one, registerModel } from '@mail/model';

registerModel({
    name: 'KanbanFieldActivityView',
    fields: {
        activityButtonView: one('ActivityButtonView', { default: {}, inverse: 'kanbanFieldActivityViewOwner', required: true }),
        id: attr({ identifying: true }),
        thread: one('Thread', { required: true }),
        webRecord: attr({ required: true }),
    },
});
