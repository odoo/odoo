/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'Rating',
    fields: {
        id: attr({
            identifying: true,
            readonly: true,
            required: true,
        }),
        ratingImageUrl: attr({
            readonly: true,
        }),
        ratingText: attr({
            readonly: true,
        }),
    },
});
