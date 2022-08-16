/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'LivechatOperator',
    fields: {
        id: attr({
            identifying: true,
            readonly: true,
            required: true,
        }),
        name: attr(),
    },
});
