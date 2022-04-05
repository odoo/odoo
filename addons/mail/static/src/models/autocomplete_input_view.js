/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: ['chatWindowOwnerAsNewMessage'],
    fields: {
        chatWindowOwnerAsNewMessage: one('ChatWindow', {
            inverse: 'newMessageAutocompleteInputView',
            readonly: true,
            required: true,
        }),
    },
});
