/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'AutocompleteInputSuggestionItemView',
    identifyingFields: ['autocompleteInputSuggestionViewOwner', 'suggestedPartner'],
    recordMethods: {
        async select() {
            const chat = await this.messaging.getChat({ partnerId: this.suggestedPartner.id });
            if (!chat) {
                return;
            }
            this.messaging.chatWindowManager.openThread(chat, {
                makeActive: true,
                replaceNewMessage: true,
            });
        },
        /**
         * @param {MouseEvent} ev 
         */
        async onClick(ev) {
            this.select();
        },
    },
    fields: {
        autocompleteInputSuggestionViewOwner: one('AutocompleteInputSuggestionView', {
            inverse: 'itemViews',
            readonly: true,
            required: true,
        }),
        autocompleteInputSuggestionViewOwnerAsActive: one('AutocompleteInputSuggestionView', {
            inverse: 'activeItemView',
            readonly: true,
        }),
        suggestedPartner: one('Partner', {
            readonly: true,
            required: true,
        }),
    },
});
