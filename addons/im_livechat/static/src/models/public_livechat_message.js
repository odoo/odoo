/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatMessage',
    identifyingFields: ['id'],
    fields: {
        data: attr(),
        id: attr({
            readonly: true,
            required: true,
        }),
        legacyPublicLivechatMessage: attr(),
    },
});
