/** @odoo-module **/

import { attr, registerModel } from '@mail/model';

registerModel({
    name: 'LivechatOperator',
    fields: {
        id: attr({
            identifying: true,
        }),
        name: attr(),
    },
});
