/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'FollowButtonView',
    identifyingFields: [['chatterOwner']],
    recordMethods: {
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsDisabled() {
            if (!this.chatterOwner) {
                return clear();
            }
            return this.chatterOwner.isDisabled;
        },
    },
    fields: {
        chatterOwner: one('Chatter', {
            inverse: 'followButtonView',
            readonly: true,
        }),
        isDisabled: attr({
            compute: '_computeIsDisabled',
        }),
    },
});
