/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChatterTopbar',
    identifyingFields: ['chatter'],
    fields: {
        chatter: one('Chatter', {
            inverse: 'topbar',
            readonly: true,
            required: true,
        }),
    },
});
