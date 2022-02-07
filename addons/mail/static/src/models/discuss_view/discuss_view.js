/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'DiscussView',
    identifyingFields: ['discuss'],
    recordMethods: {
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingItem() {
            return Boolean(
                this.sidebarAddChannelInputView ||
                this.sidebarAddChatInputView
            );
        },
    },
    fields: {
        discuss: one('Discuss', {
            inverse: 'discussView',
            readonly: true,
            required: true,
        }),
        isAddingItem: attr({
            compute: '_computeIsAddingItem',
        }),
        mobileAddChannelInputView: one('AutocompleteInputView', {
            inverse: 'discussViewOwnerAsMobileAddChannel',
            isCausal: true,
        }),
        mobileAddChatInputView: one('AutocompleteInputView', {
            inverse: 'discussViewOwnerAsMobileAddChat',
            isCausal: true,
        }),
        sidebarAddChannelInputView: one('AutocompleteInputView', {
            inverse: 'discussViewOwnerAsSidebarAddChannel',
            isCausal: true,
        }),
        sidebarAddChatInputView: one('AutocompleteInputView', {
            inverse: 'discussViewOwnerAsSidebarAddChat',
            isCausal: true,
        }),
    },
});
