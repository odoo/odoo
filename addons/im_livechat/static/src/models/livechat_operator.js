/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'LivechatOperator',
    identifyingFields: ['id'],
    fields: {
        id: attr({
            readonly: true,
            required: true,
        }),
        name: attr(),
    },
});
