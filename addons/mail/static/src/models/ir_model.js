/** @odoo-module **/

import { attr, one, registerModel } from '@mail/model';

registerModel({
    name: 'ir.model',
    fields: {
        /**
         * Determines the name of the views that are available for this model.
         */
        availableWebViews: attr({
            compute() {
                return ['kanban', 'list', 'form', 'activity'];
            },
        }),
        activityGroup: one('ActivityGroup', { inverse: 'irModel' }),
        iconUrl: attr(),
        id: attr({ identifying: true }),
        model: attr({ required: true }),
        name: attr(),
    },
});
