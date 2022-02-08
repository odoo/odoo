/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';

registerModel({
    name: 'ActivityType',
    identifyingFields: ['id'],
    fields: {
        activities: many('Activity', {
            inverse: 'type',
        }),
        displayName: attr(),
        id: attr({
            readonly: true,
            required: true,
        }),
    },
});
