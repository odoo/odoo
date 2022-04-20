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
        onClickUnfollow(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.chatterOwner || !this.chatterOwner.thread) {
                return;
            }
            this.chatterOwner.thread.unfollow();
        },
    },
    fields: {
        chatterOwner: one('Chatter', {
            inverse: 'followButtonView',
            readonly: true,
        }),
    },
});
