/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: [['chatWindowOwnerAsNewMessage', 'discussViewOwnerAsMobileAddItemHeader']],
    fields: {
        chatWindowOwnerAsNewMessage: one('ChatWindow', {
            inverse: 'newMessageAutocompleteInputView',
            readonly: true,
        }),
        discussViewOwnerAsMobileAddItemHeader: one('DiscussView', {
            inverse: 'mobileAddItemHeaderView',
            readonly: true,
        }),
    },
});
