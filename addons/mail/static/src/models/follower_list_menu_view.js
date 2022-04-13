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
         * @param {MouseEvent} ev
         */
        onClickFollower(ev) {
            this.hide();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickFollowersButton(ev) {
            this.update({ isDropdownOpen: !this.isDropdownOpen });
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
        isDropdownOpen: attr({
            default: false,
        }),
    },
});
