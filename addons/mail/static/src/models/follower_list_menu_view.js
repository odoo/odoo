/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

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
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            if (this.chatterOwner && this.chatterOwner.thread) {
                return replace(this.chatterOwner.thread);
            }
            return clear();
        }
    },
    fields: {
        chatterOwner: one('Chatter', {
            inverse: 'followerListMenuView',
            readonly: true,
        }),
        isDropdownOpen: attr({
            default: false,
        }),
        thread: one('Thread', {
            compute: '_computeThread',
        }),
    },
});
