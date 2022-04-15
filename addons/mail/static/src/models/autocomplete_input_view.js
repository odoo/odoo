/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: [[
        'chatWindowOwnerAsNewMessage',
        'discussSidebarCategoryOwnerAsAddingItem',
        'discussViewOwnerAsMobileAddItemHeader',
        'messagingMenuOwnerAsMobileNewMessageInput',
    ]],
    recordMethods: {
        /**
         * @private
         * @returns {string}
         */
        _computePlaceholder() {
            if (this.chatWindowOwnerAsNewMessage) {
                return this.chatWindowOwnerAsNewMessage.newMessageFormInputPlaceholder;
            }
            if (this.discussViewOwnerAsMobileAddItemHeader) {
                if (this.discussViewOwnerAsMobileAddItemHeader.discuss.isAddingChannel) {
                    return this.discussViewOwnerAsMobileAddItemHeader.discuss.addChannelInputPlaceholder;
                } else {
                    return this.discussViewOwnerAsMobileAddItemHeader.discuss.addChatInputPlaceholder;
                }
            }
            if (this.discussSidebarCategoryOwnerAsAddingItem) {
                return this.discussSidebarCategoryOwnerAsAddingItem.newItemPlaceholderText;
            }
            if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                return this.messagingMenuOwnerAsMobileNewMessageInput.mobileNewMessageInputPlaceholder;
            }
        },
    },
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
        placeholder: attr({
            compute: '_computePlaceholder',
        }),
    },
});
