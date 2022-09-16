/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'FollowButtonView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickFollow(ev) {
            if (!this.chatterOwner || !this.chatterOwner.thread) {
                return;
            }
            this.chatterOwner.thread.follow();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickUnfollow(ev) {
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
            this.update({ isUnfollowButtonHighlighted: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleaveUnfollow(ev) {
            this.update({ isUnfollowButtonHighlighted: false });
        },
    },
    fields: {
        chatterOwner: one('Chatter', {
            identifying: true,
            inverse: 'followButtonView',
        }),
        isDisabled: attr({
            compute() {
                if (!this.chatterOwner) {
                    return clear();
                }
                return !this.chatterOwner.hasReadAccess;
            },
        }),
        isUnfollowButtonHighlighted: attr({
            default: false,
        }),
    },
});
