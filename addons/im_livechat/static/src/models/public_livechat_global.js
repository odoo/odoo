/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatGlobal',
    identifyingFields: ['messaging'],
    fields: {
        chatbotServerUrl: attr(),
        isAvailable: attr({
            default: false,
        }),
        options: attr({
            default: {},
        }),
        serverUrl: attr({
            default: '',
        }),
    },
});
