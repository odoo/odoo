/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'FollowButtonView',
    identifyingFields: [['chatterOwner']],
    recordMethods: {
        /**
         * @param {MouseEvent} ev 
         */
        onClickFollow(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.chatterOwner.thread) {
                return;
            }
            this.chatterOwner.thread.onClickFollow(ev);
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickUnfollow(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.chatterOwner.thread) {
                return;
            }
            this.chatterOwner.thread.onClickUnfollow(ev);
        },
    },
    fields: {
        chatterOwner: one('Chatter', {
            inverse: 'followButtonView',
            readonly: true,
        }),
    },
});
