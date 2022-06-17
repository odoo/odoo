/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'InputSelectionPromptView',
    identifyingFields: ['popoverViewOwner'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
         _computeItems() {
            if (this.messaging.mediaDevices.length > 0) {
                return insertAndReplace(
                    this.messaging.mediaDevices.map(mediaDevice => ({ mediaDevice: replace(mediaDevice) }))
                );
            }
            return clear();
        },
    },
    fields: {
        items: many('InputSelectionItem', {
            compute: '_computeItems',
            inverse: 'inputSelectionPromptViewOwner',
            isCausal: true,
        }),
        popoverViewOwner: one('PopoverView', {
            inverse: 'inputSelectionPromptView',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
