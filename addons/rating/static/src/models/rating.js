/** @odoo-module **/

import { attr, Model } from '@mail/model';

Model({
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
