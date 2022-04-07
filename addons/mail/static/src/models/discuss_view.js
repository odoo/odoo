/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'DiscussView',
    identifyingFields: ['discuss'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMobileAddItemHeaderAutocompleteInputView() {
            if (
                this.messaging.device.isMobile &&
                (this.discuss.isAddingChannel || this.discuss.isAddingChat)
            ) {
                return insertAndReplace();
            }
            return clear();
        },
    },
    fields: {
        mobileAddItemHeaderAutocompleteInputView: one('AutocompleteInputView', {
            compute: '_computeMobileAddItemHeaderAutocompleteInputView',
            inverse: 'discussViewOwnerAsMobileAddItemHeader',
            isCausal: true,
        }),
        discuss: one('Discuss', {
            inverse: 'discussView',
            readonly: true,
            required: true,
        }),
    },
});
