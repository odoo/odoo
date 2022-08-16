/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'FollowButtonView',
    recordMethods: {
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsDisabled() {
            if (!this.chatterOwner) {
                return clear();
            }
            return !this.chatterOwner.hasReadAccess;
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickFollow(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.chatterOwner || !this.chatterOwner.thread) {
                return;
            }
            this.chatterOwner.thread.follow();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickUnfollow(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.chatterOwner || !this.chatterOwner.thread) {
                return;
            }
            this.chatterOwner.thread.unfollow();
            this.chatterOwner.reloadParentView({ fieldNames: ['message_follower_ids'] });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseEnterUnfollow(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isUnfollowButtonHighlighted: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleaveUnfollow(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ isUnfollowButtonHighlighted: false });
        },
    },
    fields: {
        chatterOwner: one('Chatter', {
            identifying: true,
            inverse: 'followButtonView',
            readonly: true,
        }),
        isDisabled: attr({
            compute: '_computeIsDisabled',
        }),
        isUnfollowButtonHighlighted: attr({
            default: false,
        }),
    },
});
