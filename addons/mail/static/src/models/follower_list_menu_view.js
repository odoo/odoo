/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerListMenuView',
    identifyingFields: [['chatterOwner']],
    recordMethods: {
        hide() {
            this.update({ isDropdownOpen: false });
        }
    },
    fields: {
        chatterOwner: one('Chatter', {
            inverse: 'followerListMenuView',
            readonly: true,
        }),
        /**
         * Determine whether the dropdown is open or not.
         */
        isDropdownOpen: attr({
            default: false,
        }),
    },
});
