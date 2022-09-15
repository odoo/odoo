/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'FollowerListMenuView',
    recordMethods: {
        hide() {
            this.update({ isDropdownOpen: false });
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
            identifying: true,
            inverse: 'followerListMenuView',
        }),
        followerViews: many('FollowerView', {
            compute() {
                return this.chatterOwner.thread.followers.map(follower => ({ follower }));
            },
            inverse: 'followerListMenuViewOwner',
        }),
        isDisabled: attr({
            compute() {
                return !this.chatterOwner.hasReadAccess;
            }
        }),
        isDropdownOpen: attr({
            default: false,
        }),
    },
});
