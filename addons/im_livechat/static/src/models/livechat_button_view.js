/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'LivechatButtonView',
    identifyingFields: ['messaging'],
    fields: {
        // livechat window
        chatWindow: attr({
            default: null,
        }),
    },
});
