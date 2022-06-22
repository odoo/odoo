/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'Chatbot',
    identifyingFields: ['livechatButtonViewOwner'],
    fields: {
        data: attr(),
        livechatButtonViewOwner: one('LivechatButtonView', {
            inverse: 'chatbot',
            readonly: true,
            required: true,
        }),
    },
});
