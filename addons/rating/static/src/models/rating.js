/** @odoo-module **/

import { attr, registerModel } from '@mail/model';

registerModel({
    name: 'Rating',
    fields: {
        id: attr({
            identifying: true,
        }),
        ratingImageUrl: attr({
            readonly: true,
        }),
        ratingText: attr({
            readonly: true,
        }),
    },
});
