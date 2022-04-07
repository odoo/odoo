/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: [[
        'chatWindowOwnerAsNewMessage',
        'discussSidebarCategoryOwnerAsAddingItem',
        'discussViewOwnerAsMobileAddItemHeader',
        'messagingMenuOwnerAsMobileNewMessageInput',
    ]],
    fields: {
        chatWindowOwnerAsNewMessage: one('ChatWindow', {
            inverse: 'newMessageAutocompleteInputView',
            readonly: true,
        }),
        discussSidebarCategoryOwnerAsAddingItem: one('DiscussSidebarCategory', {
            inverse: 'addingItemAutocompleteInputView',
            readonly: true,
        }),
        discussViewOwnerAsMobileAddItemHeader: one('DiscussView', {
            inverse: 'mobileAddItemHeaderAutocompleteInputView',
            readonly: true,
        }),
        messagingMenuOwnerAsMobileNewMessageInput: one('MessagingMenu', {
            inverse: 'mobileNewMessageAutocompleteInputView',
            readonly: true,
        }),
    },
});
