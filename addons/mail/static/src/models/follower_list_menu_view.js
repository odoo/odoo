/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerListMenuView',
    identifyingFields: [['chatterOwner']],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickFollowersButton(ev) {
            this.update({ isDropdownOpen: !this.isDropdownOpen });
        },
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
