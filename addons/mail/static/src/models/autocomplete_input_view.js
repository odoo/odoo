/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: [['chatWindowOwnerAsNewMessage', 'discussSidebarCategoryOwnerAsAddingItem']],
    fields: {
        chatWindowOwnerAsNewMessage: one('ChatWindow', {
            inverse: 'newMessageAutocompleteInputView',
            readonly: true,
        }),
        discussSidebarCategoryOwnerAsAddingItem: one('DiscussSidebarCategory', {
            inverse: 'addingItemAutocompleteInputView',
            readonly: true,
        }),
    },
});
