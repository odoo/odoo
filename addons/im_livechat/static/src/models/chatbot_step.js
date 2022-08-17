/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ChatbotStep',
    fields: {
        chabotOwner: one('Chatbot', {
            identifying: true,
            inverse: 'currentStep',
        }),
        data: attr(),
    },
});
