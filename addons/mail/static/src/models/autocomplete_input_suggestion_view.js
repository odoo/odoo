/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'AutocompleteInputSuggestionView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        async onClick() {
            if (!this.exists()) {
                return;
            }
            const owner = this.autocompleteInputSuggestionListView.owner;
            if (owner.chatWindowOwnerAsNewMessage) {
                owner.chatWindowOwnerAsNewMessage.onAutocompleteSelect(this.autocompleteInputSuggestable);
            } else if (owner.discussSidebarCategoryOwnerAsAddingItem) {
                owner.discussSidebarCategoryOwnerAsAddingItem.onAddItemAutocompleteSelect(this.autocompleteInputSuggestable);
            } else if (owner.discussViewOwnerAsMobileAddItemHeader) {
                owner.discussViewOwnerAsMobileAddItemHeader.onMobileAddItemHeaderInputSelect(this.autocompleteInputSuggestable);
            } else if (owner.messagingMenuOwnerAsMobileNewMessageInput) {
                owner.messagingMenuOwnerAsMobileNewMessageInput.onMobileNewMessageInputSelect(this.autocompleteInputSuggestable);
            }
            owner.hide();
        },
    },
    fields: {
        autocompleteInputSuggestable: one('AutocompleteInputSuggestable', {
            identifying: true,
            inverse: 'suggestionView',
        }),
        autocompleteInputSuggestionListView: one('AutocompleteInputSuggestionListView', {
            identifying: true,
            inverse: 'suggestionViews',
        }),
        displayName: attr({
            compute() {
                if (this.autocompleteInputSuggestable.ownerAsCreatingChannel) {
                    return "Create #" + this.autocompleteInputSuggestable.nameToCreateChannel;
                }
                if (this.autocompleteInputSuggestable.partner) {
                    return this.autocompleteInputSuggestable.partner.nameOrDisplayName;
                }
                if (this.autocompleteInputSuggestable.channel) {
                    return this.autocompleteInputSuggestable.channel.displayName;
                }
                return "";
            }
        }),
        isActive: attr({
            compute() {
                return this === this.autocompleteInputSuggestionListView.activeSuggestionView;
            }
        }),
    },
});
