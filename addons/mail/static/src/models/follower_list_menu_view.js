/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerListMenuView',
    identifyingFields: [['chatterOwner']],
    recordMethods: {
        hide() {
            this.update({ isDropdownOpen: false });
        },
        /**
         * @param {KeyboardEvent} ev
         */
        onKeydown(ev) {
            ev.stopPropagation();
            switch (ev.key) {
                case 'Escape':
                    ev.preventDefault();
                    this.hide();
                    break;
            }
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
