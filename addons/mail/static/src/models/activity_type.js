/** @odoo-module **/

import { attr, many, registerModel } from '@mail/model';

registerModel({
    name: 'ActivityType',
    fields: {
        activities: many('Activity', { inverse: 'type' }),
        displayName: attr(),
        id: attr({ identifying: true }),
    },
});
