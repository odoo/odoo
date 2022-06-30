/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatGlobal',
    identifyingFields: ['messaging'],
    fields: {
        isAvailable: attr({
            default: false,
        }),
    },
});
