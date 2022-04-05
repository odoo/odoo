/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: [['chatWindowOwnerAsNewMessage', 'messagingMenuOwnerAsMobileNewMessageInput']],
    fields: {
        chatWindowOwnerAsNewMessage: one('ChatWindow', {
            inverse: 'newMessageAutocompleteInputView',
            readonly: true,
        }),
        messagingMenuOwnerAsMobileNewMessageInput: one('MessagingMenu', {
            inverse: 'mobileNewMessageInputAutocompleteView',
            readonly: true,
        }),
    },
});
