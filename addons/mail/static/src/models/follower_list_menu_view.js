/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

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
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFollowerViews() {
            return insertAndReplace(this.chatterOwner.thread.followers.map(follower => {
                return { follower };
            }));
        },
        /**
         * @private
         * @returns {Boolean}
         */
        _computeIsDisabled() {
            return !this.chatterOwner.hasReadAccess;
        }
    },
    fields: {
        chatterOwner: one('Chatter', {
            identifying: true,
            inverse: 'followerListMenuView',
        }),
        followerViews: many('FollowerView', {
            compute: '_computeFollowerViews',
            inverse: 'followerListMenuViewOwner',
            isCausal: true,
        }),
        isDisabled: attr({
            compute: '_computeIsDisabled',
        }),
        isDropdownOpen: attr({
            default: false,
        }),
    },
});
