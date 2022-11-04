/** @odoo-module **/

import { attr, one, registerModel } from '@mail/model';

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
