/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatGlobal',
    identifyingFields: ['messaging'],
    fields: {
        chatbotServerUrl: attr(),
        feedbackView: one('PublicLivechatFeedbackView', {
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
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
