/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';

registerModel({
    name: 'ActivityType',
    fields: {
        activities: many('Activity', {
            inverse: 'type',
        }),
        displayName: attr(),
        id: attr({
            identifying: true,
            readonly: true,
            required: true,
        }),
    },
});
