/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'LivechatButtonView',
    identifyingFields: ['messaging'],
    fields: {
        isChatbot: attr({
            default: false,
        }),
    },
});
