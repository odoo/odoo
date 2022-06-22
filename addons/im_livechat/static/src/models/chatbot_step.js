/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ChatbotStep',
    identifyingFields: ['chabotOwner'],
    fields: {
        chabotOwner: one('Chatbot', {
            inverse: 'currentStep',
            readonly: true,
            required: true,
        }),
        data: attr(),
    },
});
